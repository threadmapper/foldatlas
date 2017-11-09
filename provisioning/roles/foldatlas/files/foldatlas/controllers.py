
import json
import os
import settings
import uuid

from math import ceil

from sqlalchemy import func

from models import (Transcript,
                    NucleotideMeasurementRun,
                    NucleotideMeasurementSet,
                    Structure,
                    GeneLocation,
                    StructurePredictionRun,
                    values_str_unpack_float,
                    values_str_unpack_int,
                    RawReactivities,
                    RawReplicateCounts)

from utils import ensure_dir, insert_newlines, build_dot_bracket

import database


# Fetches sequence annotation data from the DB and sends it to the genome
# browser front end as JSON.

class GenomeBrowser:
    def get_transcripts( self, request ):
        chromosome_id = "Chr" + str( int( request.args.get( 'chr' ) ) )  # SQL-injection safe
        start = int( request.args.get( 'start' ) )
        end = int( request.args.get( 'end' ) )

        # Retrieve features using the gene location cache table
        sql = """
            SELECT
                f.*
            FROM
                        gene_location AS gl
            INNER JOIN  transcript    AS t  ON  t.gene_id       = gl.gene_id 
            INNER JOIN  feature       AS f  ON  f.strain_id     = gl.strain_id  AND
                                                f.transcript_id = t.id 
            WHERE
                gl.strain_id      = '{strain}'
            AND gl.chromosome_id  = '{chromo}' 
            AND gl.end            > {start_} 
            AND gl.start          < {end_} """

        sql = sql.format( strain=settings.v1_ids.strain_id,
                          chromo=chromosome_id,
                          start_=start,
                          end_=end ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        # collect transcript data
        transcripts = { }
        feature_rows = [ ]

        for result in results:
            if result.transcript_id not in transcripts:
                transcripts[ result.transcript_id ] = {
                    "Parent": result.transcript_id,
                    "feature_type": "transcript",  # without this, it won't draw
                    "direction": result.direction,
                    "start": None,
                    "end": None,
                    "id": result.transcript_id
                }

            transcript = transcripts[ result.transcript_id ]

            # keep track of total start and end
            if transcript[ "start" ] is None or result.start < transcript[ "start" ]:
                transcript[ "start" ] = result.start
            if transcript[ "end" ] is None or result.end > transcript[ "end" ]:
                transcript[ "end" ] = result.end

            feature_rows.append( result )

        out = [ ]

        # add the transcript metadata to the output. make sure the transcripts are added
        # in alphabetical order
        transcript_ids = [ ]
        for transcript_id in transcripts:
            transcript_ids.append( transcript_id )

        transcript_ids = sorted( transcript_ids )
        for transcript_id in transcript_ids:
            out.append( transcripts[ transcript_id ] )

        # also add all the feature metadata to the output
        for feature_row in feature_rows:
            out.append( {
                "Parent": feature_row.transcript_id,
                "feature_type": feature_row.type_id,
                "direction": result.direction,
                "start": feature_row.start,
                "end": feature_row.end,
                "id": feature_row.transcript_id + "-" + str( feature_row.id )
            } )

        return json.dumps( out )

    @staticmethod
    def get_genes( request ):
        chromosome_id = "Chr" + str( int( request.args.get( 'chr' ) ) )  # SQL-injection safe
        start = int( request.args.get( 'start' ) )
        end = int( request.args.get( 'end' ) )

        # fetch gene data from the location cache table.
        sql = """
            SELECT
                *
            FROM
                gene_location
            WHERE 
                strain_id     = '{strain_id}'       AND
                chromosome_id = '{chromosome_id}'   AND
                `end`         > {start_}            AND
                `start`       < {end_} """

        sql = sql.format( strain_id=settings.v1_ids.strain_id,
                          chromosome_id=chromosome_id,
                          start_=start,
                          end_=end ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        out = [ ]
        for result in results:
            out.append( {
                "feature_type": "gene",  # without this, it won't draw
                "direction": result.direction,
                "id": result.gene_id,
                "start": result.start,
                "end": result.end,
            } )

        buf = json.dumps( out )

        return buf

    # Fetch chromosome IDs and their lengths. Used for chromosome menu and also initialising the genome browser.
    def get_chromosomes( self ):
        sql = """ 
            SELECT 
                chromosome_id, 
                CHAR_LENGTH( sequence ) AS length 
            FROM 
                chromosome 
            WHERE
                strain_id = '{strain_id}' 
            ORDER BY 
                chromosome_id ASC """

        sql = sql.format( strain_id=settings.v1_ids.strain_id ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        out = [ ]
        for result in results:
            out.append( {
                "chromosome_id": result.chromosome_id,
                "length": result.length,
                "int_id": int( result.chromosome_id[ 3 ] )
            } )

        return out


class TranscriptView:
    def __init__( self, transcript_id ):
        self.transcript_id = transcript_id

        strain_id = settings.v1_ids.strain_id

        # Get the coords of the associated gene
        data = database.db_session \
            .query( Transcript, GeneLocation ) \
            .filter( Transcript.id == transcript_id,
                     Transcript.gene_id == GeneLocation.gene_id,
                     GeneLocation.strain_id == strain_id ) \
            .all()

        self.gene_id = data[ 0 ][ 1 ].gene_id

        self.transcript_data = json.dumps( { "gene_id": self.gene_id,
                                             "transcript_id": transcript_id,
                                             "chromosome_id": data[ 0 ][ 1 ].chromosome_id,
                                             "start": data[ 0 ][ 1 ].start,
                                             "end": data[ 0 ][ 1 ].end } )

        self.structure_view = StructureView( transcript_id=self.transcript_id,
                                             strain_id=strain_id )

        self.nucleotide_measurement_view = NucleotideMeasurementView( transcript_id=self.transcript_id,
                                                                      strain_id=strain_id )

        self.empty = self.structure_view.empty and self.nucleotide_measurement_view.empty

        # disable alignment view... revisit later with SNPstructure
        # self.alignment_view = AlignmentView(self.transcript_id)


class NucleotideMeasurementView:
    def __init__( self, transcript_id, strain_id ):
        self.transcript_id = transcript_id
        self.strain_id = strain_id
        self.empty = True
        self.data_json = self._build_entries( [ settings.v1_ids.nucleotide_measurement_run_id ] )

    def _build_entries( self, experiment_ids ):
        # Load experiments
        experiments = database.db_session \
            .query( NucleotideMeasurementRun ) \
            .filter( NucleotideMeasurementRun.id.in_( experiment_ids ) ) \
            .all()

        # Load measurements
        measurements_data = database.db_session \
            .query( NucleotideMeasurementSet ) \
            .filter( NucleotideMeasurementSet.nucleotide_measurement_run_id.in_( experiment_ids ),
                     NucleotideMeasurementSet.transcript_id == self.transcript_id ) \
            .all()

        data = { }

        seq_str = str( Transcript( self.transcript_id ).get_sequence( self.strain_id ).seq )

        # Populate experiment rows
        for experiment in experiments:
            experiment_data = dict( id=experiment.id, description=experiment.description )
            experiment_data[ "data" ] = [ { "position": n,
                                            "nuc": nt,
                                            "measurement": None } for n, nt in enumerate( seq_str ) ]

            data[ experiment.id ] = experiment_data

        # Add measurements to each experiment json element
        # Loop since we might be dealing with > 1 measurement set
        for measurement_set in measurements_data:
            experiment_id = measurement_set.nucleotide_measurement_run_id
            measurements = values_str_unpack_float( measurement_set.values )

            for pos, measurement in enumerate( measurements ):
                data[ experiment_id ][ "data" ][ pos ][ "measurement" ] = measurement

        # For each experiment, check whether there is no data and set empty flags accordingly.
        self.empty = True  # all empty flag
        for experiment_id in data:
            entry = data[ experiment_id ]

            empty = True
            for pos in entry[ "data" ]:
                if pos[ "measurement" ] and pos[ "measurement" ] != 0:
                    empty = False
                    self.empty = False

            if empty:
                del entry[ "data" ]
                entry[ "empty" ] = True
            else:
                entry[ "empty" ] = False

        return json.dumps( data )


class TranscriptSearcher:
    @staticmethod
    def search( search_string ):
        from flask import abort

        transcripts = database.db_session \
            .query( Transcript ) \
            .filter( Transcript.id.like( "%" + search_string + "%" ) ) \
            .all()

        if len( transcripts ) == 0:  # no transcripts found
            abort( 404 )

        out = [ transcript.id for transcript in transcripts ]

        return json.dumps( out )


class CoverageSearcher:
    def __init__( self ):
        self.page_size = 25

        # TODO these hard-coded values must become session-specific

        # The experiment ID to sort by.
        # Ideally this should have a value for each # transcript,
        # otherwise there will be some missing transcripts...

        self._strain_id = settings.v1_ids.strain_id
        self._nucleotide_measurement_run_id = settings.v1_ids.nucleotide_measurement_run_id
        self._structure_prediction_run_id = settings.v1_ids.in_vivo_structure_prediction_run_id

    def fetch_page_count( self ):
        transcript_count = database.db_session \
            .query( func.count( '*' ) ) \
            .select_from( NucleotideMeasurementSet ) \
            .filter( NucleotideMeasurementSet.nucleotide_measurement_run_id == self._nucleotide_measurement_run_id ) \
            .scalar()

        page_count = ceil( transcript_count / self.page_size )
        return page_count

    def fetch_transcript_data( self, page_num ):
        offset = (int( page_num ) - 1) * self.page_size
        limit = self.page_size

        sql = """
            SELECT
                t.id                            AS transcript_id,
                gl.end - gl.start + 1           AS gene_length,
                jnms.coverage                   AS coverage,
                jnms.structure_transcript_id    AS structure_transcript_id
            FROM
                (
                SELECT
                    nms.*,
                    s.transcript_id AS structure_transcript_id
                FROM
                    (
                    SELECT
                        *
                    FROM
                        nucleotide_measurement_set
                    WHERE
                        nucleotide_measurement_run_id = {nt_run_id} 
                    ORDER BY
                        coverage DESC
                    LIMIT {limit_} OFFSET {offset_}
                    ) AS nms
                 LEFT OUTER JOIN structure AS s   ON  s.transcript_id                 = nms.transcript_id   AND
                                                      s.structure_prediction_run_id   = {sp_run_id}
                ) AS jnms
                INNER JOIN transcript      AS t   ON  t.id                            = jnms.transcript_id
                INNER JOIN gene_location   AS gl  ON  t.gene_id                       = gl.gene_id 
            WHERE
                gl.strain_id = '{strain_id}'
            GROUP BY
                transcript_id
            ORDER BY
                coverage DESC """

        sql = sql.format( nt_run_id=self._nucleotide_measurement_run_id,
                          limit_=limit,
                          offset_=offset,
                          sp_run_id=self._structure_prediction_run_id,
                          strain_id=self._strain_id ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        out = [ ]
        for row in results:
            out.append( { "transcript_id": row[ "transcript_id" ],
                          "gene_length": row[ "gene_length" ],
                          "coverage": row[ "coverage" ],
                          "has_structure": row[ "structure_transcript_id" ] is not None } )

        return out


class StructureView:
    def __init__( self, transcript_id, strain_id ):
        self.transcript_id = transcript_id
        self.strain_id = strain_id
        self.empty = True
        self.data_json = None

        self.build_entries( structure_prediction_run_ids=settings.v1_ids.structure_prediction_run_ids )

    def build_entries( self, structure_prediction_run_ids ):

        from models import Structure, StructurePredictionRun

        # Load experiments
        runs = database.db_session \
            .query( StructurePredictionRun ) \
            .filter( StructurePredictionRun.id.in_( structure_prediction_run_ids ) ) \
            .all()

        data = { }

        for run in runs:
            run_data = { "id": run.id,
                         "description": run.description,
                         "data": [ ] }

            # fetch all Structure objects that match the experiment ID and the transcript ID
            results = database.db_session \
                .query( Structure ) \
                .filter( Structure.structure_prediction_run_id == run.id,
                         Structure.transcript_id == self.transcript_id ) \
                .all()

            # add the structures to output json
            for structure in results:
                run_data[ "data" ].append( { "id": structure.id,
                                             "energy": structure.energy,
                                             "pc1": structure.pc1,
                                             "pc2": structure.pc2 } )

            data[ run.id ] = run_data

        self.empty = True

        for experiment_id in data:
            entry = data[ experiment_id ]
            if len( entry[ "data" ] ) > 0:
                self.empty = False

        if not self.empty:
            self.data_json = json.dumps( data )


class StructureDiagramView:
    """
    Plots a single RNA structure using the RNAplot program from the ViennaRNA package.
    """

    def __init__( self, structure_id ):
        self.structure_id = structure_id
        self.data_json = self._build_plot()

    def _build_plot( self ):
        # convert entities to dot bracket string
        data = self._build_dot_bracket()

        # use ViennaRNA to get 2d plot coords
        data[ "coords" ] = self._get_vienna_layout( data )

        # return the results as a json string
        return json.dumps( data )

    def _build_dot_bracket( self ):
        # get all the positions
        results = database.db_session \
            .query( Structure, Transcript ) \
            .filter( Structure.id == self.structure_id,
                     Transcript.id == Structure.transcript_id ) \
            .all()

        # Get position values from Structure entity
        positions = results[ 0 ][ 0 ].get_values()
        seq_str = results[ 0 ][ 1 ].get_sequence_str()
        dot_bracket_str = build_dot_bracket( positions )

        return { "sequence": seq_str.replace( "T", "U" ),
                 "structure": dot_bracket_str }

    # Grab 2d coords from viennaRNA
    # There is a python2 wrapper for vienna RNA but not python 3 compatible
    @staticmethod
    def _get_vienna_layout( data ):

        temp_folder = "/tmp/" + str( uuid.uuid4() )
        ensure_dir( temp_folder )
        dot_bracket_filepath = temp_folder + "/dotbracket.txt"

        f = open( dot_bracket_filepath, "w" )
        f.write( data[ "sequence" ] + "\n" + data[ "structure" ] + "\n" )
        f.close()

        # change to tmp folder
        os.chdir( temp_folder )

        # use RNAplot CLI to generate the xrna tab delimited file
        os.system( "RNAplot -o xrna < " + dot_bracket_filepath )

        # get the coords out by parsing the file
        coords = [ ]
        with open( temp_folder + "/rna.ss" ) as f:
            for line in f:
                line = line.strip()
                if line == "" or line[ 0 ] == "#":
                    continue

                bits = line.split()
                x = float( bits[ 2 ] )
                y = float( bits[ 3 ] )
                coords.append( [ x, y ] )

        os.system( "rm -rf " + temp_folder )

        return coords


class StructureCirclePlotView( object ):
    def __init__( self, structure_id ):
        self.structure_id = structure_id
        self.data_json = self._get_values()

    def _get_values( self ):
        # get all the positions
        results = database.db_session \
            .query( Structure ) \
            .filter( Structure.id == self.structure_id ) \
            .all()

        result = results[ 0 ]
        positions = result.get_values()
        bpps = result.get_bpp_values()

        # build the output. backward facing links are left blank
        # results must be shifted back to array indexes, since they start at 1 in the DB.
        out = [ ]
        for curr_position in range( 1, len( positions ) + 1 ):
            paired_to_position = positions[ curr_position - 1 ]

            if paired_to_position == 0 or paired_to_position < curr_position:
                link = None
            else:
                link = int( paired_to_position - 1 )

            out.append( { "name": curr_position - 1,
                          "link": link,
                          "bpp": None if bpps is None else bpps[ curr_position - 1 ] } )

        return json.dumps( out )


# Generates plaintext structure text files for download
class StructureDownloader( object ):
    def __init__( self, structure_prediction_run_ids, transcript_id ):
        """
        :param structure_prediction_run_ids:
        :param transcript_id:
        """
        self.structure_prediction_run_ids = structure_prediction_run_ids
        self.transcript_id = transcript_id

    def generate( self ):
        # Fetch the data
        results = database.db_session \
            .query( Structure, StructurePredictionRun, Transcript ) \
            .filter( StructurePredictionRun.id == Structure.structure_prediction_run_id,
                     Structure.structure_prediction_run_id.in_( self.structure_prediction_run_ids ),
                     Structure.transcript_id == self.transcript_id,
                     Transcript.id == self.transcript_id ) \
            .order_by( Structure.structure_prediction_run_id,
                       Structure.id ) \
            .all()

        return self._generate_txt( results )

    # Generates text using a more compact file format
    def _generate_txt( self, results ):
        # first we must extract and display the sequence, using the transcript object. output
        # in fasta-like format
        transcript = results[ 0 ][ 2 ]

        output_text = [ '>{}\n'.format( self.transcript_id ),
                        insert_newlines( transcript.get_sequence_str() ) ]

        # buf = ">" + self.transcript_id + "\n"
        # buf += insert_newlines( transcript.get_sequence_str() ) + "\n"

        for result in results:
            structure = result[ 0 ]
            run = result[ 1 ]
            positions = structure.get_values()

            # generate and add the header text for this structure
            output_text.append( '\n>sid_{}\tENERGY:{} kcal/mol\t{}\n'.format( structure.id,
                                                                              structure.energy,
                                                                              run.description ) )

            # generate and add dot bracket text
            output_text.append( insert_newlines( build_dot_bracket( positions ) ) )

        # return buf
        return ''.join( output_text )


class NucleotideMeasurementDownloader( object ):
    """
    Generates plain text nucleotide measurements for user download
    Includes raw and normalised
    """

    def __init__( self, nucleotide_measurement_run_id, transcript_id ):
        self.nucleotide_measurement_run_id = nucleotide_measurement_run_id
        self.transcript_id = transcript_id

    # Retrieves raw reactivity values and outputs as text
    def get_raw( self ):
        seq_str = Transcript( self.transcript_id ).get_sequence_str()

        # Use the ORM to grab compiled counts
        results = database.db_session \
            .query( RawReactivities ) \
            .filter( RawReactivities.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                     RawReactivities.transcript_id == self.transcript_id ) \
            .all()

        measurement_set = results[ 0 ]
        # minus_unpacked =
        # plus_unpacked = values_str_unpack_int(measurement_set.plus_values)

        cols = [ values_str_unpack_int( measurement_set.minus_values ),
                 values_str_unpack_int( measurement_set.plus_values ) ]

        # Grab the raw replicate lanes data
        lanes = database.db_session \
            .query( RawReplicateCounts ) \
            .filter( RawReplicateCounts.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                     RawReplicateCounts.transcript_id == self.transcript_id ) \
            .order_by(
                RawReplicateCounts.minusplus_id,
                RawReplicateCounts.bio_replicate_id,
                RawReplicateCounts.tech_replicate_id ) \
            .all()

        # gather the data
        tech_rep_ids = set()
        for lane in lanes:
            cols.append( values_str_unpack_int( lane.values ) )
            tech_rep_ids.add( lane.tech_replicate_id )

        # make headers
        headers = [ ]
        for lane in lanes:
            # tech replicate notation only added for experiments with > 1 tech replicate
            tech_str = "" if len( tech_rep_ids ) == 1 else "_T" + str( lane.tech_replicate_id )
            headers.append( str( lane.minusplus_id ) + "_B" + str( lane.bio_replicate_id ) + tech_str )

        # Build and return the output
        buf = "position\tsequence\tsum_minus\tsum_plus\t" + "\t".join( headers ) + "\n"
        for n in range( 0, len( cols[ 0 ] ) ):
            # add position and seq letter
            buf += str( n + 1 ) + "\t" + seq_str[ n ]
            for col in cols:  # add the dynamic columns
                buf += "\t" + str( int( col[ n ] ) )
            buf += "\n"
        return buf

    # Retrieves normalised reactivities and outputs as text
    def get_normalised( self ):
        # Grab sequence string
        seq_str = Transcript( self.transcript_id ).get_sequence_str()

        # Use the ORM to grab all the normalised stuff
        results = database.db_session \
            .query( NucleotideMeasurementSet ) \
            .filter( NucleotideMeasurementSet.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                     NucleotideMeasurementSet.transcript_id == self.transcript_id ) \
            .all()

        measurement_set = results[ 0 ]

        # TODO detect whether float or int and use the correct unpacker.
        # Needed for raw count values download option
        unpacked = values_str_unpack_float( measurement_set.values )

        # index measurements by pos
        measurements = { }
        for pos in range( len( unpacked ) ):
            value = unpacked[ pos ]
            measurements[ pos + 1 ] = "NA" if value is None else value

        # build the output string
        buf = [ ]

        for pos, nt in enumerate( seq_str, start=1 ):
            measurement = measurements[ pos ] if pos in measurements else 'NA'
            buf.append( '{}\t{}\t{}'.format( pos, nt, measurement ) )

        return '\n'.join( buf )
