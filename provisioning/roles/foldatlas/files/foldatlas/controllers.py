# from sqlalchemy import and_
import json
import uuid
import settings
import os

from sqlalchemy import func
from math import ceil

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

class GenomeBrowser():
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

        sql = sql.format( strain=settings.reference_strain_id,
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

    def get_genes( self, request ):
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
                'end'         > {start_}            AND
                'start'       < {end_} """

        sql = sql.format( strain_id=settings.reference_strain_id,
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

        sql = sql.format( strain_id=settings.reference_strain_id ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        out = [ ]
        for result in results:
            out.append( {
                "chromosome_id": result.chromosome_id,
                "length": result.length,
                "int_id": int( result.chromosome_id[ 3 ] )
            } )

        return out


class TranscriptView():
    def __init__( self, transcript_id ):
        self.transcript_id = transcript_id

        # Get the coords of the associated gene
        data = database.db_session \
            .query( Transcript, GeneLocation ) \
            .filter( Transcript.id == transcript_id,
                     Transcript.gene_id == GeneLocation.gene_id,
                     GeneLocation.strain_id == settings.reference_strain_id ) \
            .all()

        self.gene_id = data[ 0 ][ 1 ].gene_id

        self.transcript_data = json.dumps( {
            "gene_id": self.gene_id,
            "transcript_id": transcript_id,
            "chromosome_id": data[ 0 ][ 1 ].chromosome_id,
            "start": data[ 0 ][ 1 ].start,
            "end": data[ 0 ][ 1 ].end
        } )

        self.structure_view = StructureView( self.transcript_id, settings.reference_strain_id )
        self.nucleotide_measurement_view = NucleotideMeasurementView( self.transcript_id, settings.reference_strain_id )

        self.empty = self.structure_view.empty and self.nucleotide_measurement_view.empty

        # disable alignment view... revisit later with SNPstructure
        # self.alignment_view = AlignmentView(self.transcript_id)


class NucleotideMeasurementView():
    def __init__( self, transcript_id, strain_id ):
        self.transcript_id = transcript_id
        self.strain_id = strain_id
        self.build_entries( [ 1 ] )

    def build_entries( self, experiment_ids ):
        # Load experiments
        experiments = database.db_session \
            .query( NucleotideMeasurementRun ) \
            .filter( NucleotideMeasurementRun.id.in_( experiment_ids ) ) \
            .all()

        # Load measurements
        seq_str = str( Transcript( self.transcript_id ).get_sequence( self.strain_id ).seq )
        measurements_data = database.db_session \
            .query( NucleotideMeasurementSet ) \
            .filter( NucleotideMeasurementSet.nucleotide_measurement_run_id.in_( experiment_ids ),
                     NucleotideMeasurementSet.transcript_id == self.transcript_id ) \
            .all()

        data = { }

        # Populate experiment rows
        for experiment in experiments:
            experiment_data = {
                "id": experiment.id,
                "description": experiment.description,
                "data": [ ]
            }

            for n in range( len( seq_str ) ):  # initialise the array
                experiment_data[ "data" ].append( {
                    "position": n,
                    "nuc": seq_str[ n ],
                    "measurement": None
                } )
            data[ experiment.id ] = experiment_data

        # Add measurements to each experiment json element
        # Loop since we might be dealing with > 1 measurement set
        for measurement_set in measurements_data:
            experiment_id = measurement_set.nucleotide_measurement_run_id
            measurements = values_str_unpack_float( measurement_set.values )

            for pos in range( 0, len( measurements ) ):
                measurement = measurements[ pos ]
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

        self.data_json = json.dumps( data )


# Commented out by HW on 2017-10-09 because alignments are not currently viewed in foldatlas.
#
# class AlignmentView():
#     alignment_line_length = 80
#
#     def __init__( self, transcript_id ):
#         self.transcript_id = transcript_id
#         self.build_alignment_entries()
#
#     def build_alignment_entries( self ):
#         self.alignment_rows = [ ]
#
#         # fetch the alignment rows from the DB, using the ORM
#         alignment_entries = database.db_session \
#             .query( AlignmentEntry ) \
#             .filter( AlignmentEntry.transcript_id == self.transcript_id ) \
#             .all()
#
#         if (len( alignment_entries ) == 0):
#             return  # not enough transcripts to align
#
#         aln_len = len( alignment_entries[ 0 ].sequence )  # length of alignment, including gaps
#         row_n = 0
#         reached_end = False
#         seq_len_processed = 0
#
#         # initialise tot_nucs counters. these are for showing nuc counts at the ends of each alignment row.
#         nuc_counts = { }
#         for alignment_entry in alignment_entries:
#             nuc_counts[ alignment_entry.strain_id ] = 0
#
#         while (True):  # Each iteration builds 1 row of alignment data
#
#             start = row_n * self.alignment_line_length
#             end = start + self.alignment_line_length
#
#             if aln_len < end:
#                 reached_end = True
#                 end = aln_len
#
#             self.alignment_rows.append( {
#                 "strain_data": { },
#                 "diff": list( "*" * (end - start) )
#             } )
#
#             # create diff - as "*" - then change to "." when a difference is encountered
#             # create alignment entries data structure, for showing the sequences
#             for alignment_entry in alignment_entries:
#                 self.alignment_rows[ row_n ][ "strain_data" ][ alignment_entry.strain_id ] = {
#                     "nuc_count": 0,  # TODO fill this shiz out
#                     "sequence": list( alignment_entry.sequence[ start: end ] )
#                 }
#
#             # Loop through each nucleotide in the sequence. Determine any differences between the
#             # strains at the position of interest. Store in "diff" variable
#             for n in range( start, end ):
#                 different = False
#                 old_nuc = None
#                 for alignment_entry in alignment_entries:
#                     new_nuc = alignment_entry.sequence[ n ]
#
#                     if new_nuc != "-":  # keep track of nucleotide counts, for showing on the end
#                         nuc_counts[ alignment_entry.strain_id ] += 1
#
#                     if old_nuc != None and new_nuc != old_nuc:
#                         self.alignment_rows[ row_n ][ "diff" ][ n - start ] = "."
#                     old_nuc = new_nuc
#
#             # add nucleotide counts to the ends of the sequence alignment.
#             for alignment_entry in alignment_entries:
#                 self.alignment_rows[ row_n ][ "strain_data" ][ alignment_entry.strain_id ][ "nuc_count" ] = nuc_counts[
#                     alignment_entry.strain_id ]
#
#             if reached_end:
#                 break
#
#             row_n += 1


class TranscriptSearcher():
    def search( self, search_string ):
        from flask import abort

        transcripts = database.db_session \
            .query( Transcript ) \
            .filter( Transcript.id.like( "%" + search_string + "%" ) ) \
            .all()

        if len( transcripts ) == 0:  # no transcripts found
            abort( 404 )

        out = [ ]
        for transcript in transcripts:
            out.append( transcript.id )

        return json.dumps( out )


class CoverageSearcher():
    def __init__( self ):
        # size of pages
        self.page_size = 25

        # The experiment ID to sort by. Ideally this should have a value for each
        # transcript, otherwise there will be some missing transcripts...
        self.nucleotide_measurement_run_id = 1

    def fetch_page_count( self ):
        transcript_count = database.db_session \
            .query( func.count( '*' ) ) \
            .select_from( NucleotideMeasurementSet ) \
            .filter( NucleotideMeasurementSet.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id ) \
            .scalar()

        page_count = ceil( transcript_count / self.page_size )
        return page_count

    def fetch_transcript_data( self, page_num ):
        # TODO these hard-coded values must become session-specific
        strain_id = 'Col_0'
        nucleotide_measurement_run_id = 1
        structure_prediction_run_id = 2

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

        sql = sql.format( nt_run_id=nucleotide_measurement_run_id,
                          limit_=limit,
                          offset_=offset,
                          sp_run_id=structure_prediction_run_id,
                          strain_id=strain_id ).replace( '\n', ' ' )

        results = database.engine.execute( sql )

        out = [ ]
        for row in results:
            out.append( {
                "transcript_id": row[ "transcript_id" ],
                "gene_length": row[ "gene_length" ],
                "coverage": row[ "coverage" ],
                "has_structure": row[ "structure_transcript_id" ] is not None
            } )

        return out

        # q = database.db_session \
        #     .query(NucleotideMeasurementSet, Transcript, GeneLocation,) \
        #     .filter(
        #         NucleotideMeasurementSet.nucleotide_measurement_run_id==self.nucleotide_measurement_run_id,
        #         Transcript.id==NucleotideMeasurementSet.transcript_id,
        #         Transcript.gene_id==GeneLocation.gene_id,
        #         GeneLocation.strain_id==settings.reference_strain_id # get this for gene len
        #     ) \
        #     .outerjoin(( # Left join to find in-vivo structures for structure indicator
        #         Structure,
        #         and_(
        #             Structure.transcript_id==NucleotideMeasurementSet.transcript_id,

        #             # this filters so it's only in vivo joined against
        #             Structure.structure_prediction_run_id==2
        #         )
        #     )) \
        #     .add_entity(Structure) \
        #     .group_by(Transcript.id) \
        #     .order_by(NucleotideMeasurementSet.coverage.desc()) \
        #     .offset((int(page_num) - 1) * self.page_size) \
        #     .limit(str(self.page_size)) \

        # GROUP BY eliminates structures with the same transcript ID \

        # results = q.all()

        # tl.log("c")
        # tl.dump()

        # get the SQL so we can optimise the query
        # from sqlalchemy.dialects import postgresql
        # q_str = str(q.statement.compile(compile_kwargs={"literal_binds": True}))
        # print(q_str)

        # mandatory in vivo query - just for screenshot purposes
        # results = database.db_session \
        #     .query(NucleotideMeasurementSet, Transcript, GeneLocation, Structure, ) \
        #     .filter(
        #         NucleotideMeasurementSet.nucleotide_measurement_run_id==self.nucleotide_measurement_run_id,
        #         Transcript.id==NucleotideMeasurementSet.transcript_id,
        #         Transcript.gene_id==GeneLocation.gene_id,
        #         GeneLocation.strain_id==settings.reference_strain_id, # get this for gene len
        #         Structure.transcript_id==NucleotideMeasurementSet.transcript_id,

        #         # this filters so it's only in vivo considered
        #         Structure.structure_prediction_run_id==2
        #     ) \
        #     .add_entity(Structure) \
        #     .group_by(NucleotideMeasurementSet.transcript_id) \
        #     .order_by(NucleotideMeasurementSet.coverage.desc()) \
        #     .offset((int(page_num) - 1) * self.page_size) \
        #     .limit(str(self.page_size)) \
        #     .all()


class StructureView():
    def __init__( self, transcript_id, strain_id ):
        self.transcript_id = transcript_id
        self.strain_id = strain_id
        self.build_entries( [ 1, 2 ] )

    def build_entries( self, structure_prediction_run_ids ):

        from models import Structure, StructurePredictionRun

        # Load experiments
        runs = database.db_session \
            .query( StructurePredictionRun ) \
            .filter( StructurePredictionRun.id.in_( structure_prediction_run_ids ) ) \
            .all()

        data = { }

        for run in runs:

            run_data = {
                "id": run.id,
                "description": run.description,
                "data": [ ]
            }

            # fetch all Structure objects that match the experiment ID and the transcript ID
            results = database.db_session \
                .query( Structure ) \
                .filter(
                    Structure.structure_prediction_run_id == run.id,
                    Structure.transcript_id == self.transcript_id
            ) \
                .all()

            # add the structures to output json
            for structure in results:
                run_data[ "data" ].append( {
                    "id": structure.id,
                    "energy": structure.energy,
                    "pc1": structure.pc1,
                    "pc2": structure.pc2
                } )

            data[ run.id ] = run_data

        self.empty = True
        for experiment_id in data:
            entry = data[ experiment_id ]
            if len( entry[ "data" ] ) > 0:
                self.empty = False

        if not self.empty:
            self.data_json = json.dumps( data )


# Plots a single RNA structure using the RNAplot program from the ViennaRNA package.
class StructureDiagramView():
    def __init__( self, structure_id ):
        self.structure_id = structure_id
        self.build_plot()

    def build_plot( self ):
        # convert entities to dot bracket string
        data = self.build_dot_bracket()

        # use ViennaRNA to get 2d plot coords
        data[ "coords" ] = self.get_vienna_layout( data )

        # return the results as a json string
        self.data_json = json.dumps( data )

    def build_dot_bracket( self ):
        # get all the positions
        results = database.db_session \
            .query( Structure, Transcript ) \
            .filter(
                Structure.id == self.structure_id,
                Transcript.id == Structure.transcript_id
        ) \
            .all()

        # Get position values from Structure entity
        positions = results[ 0 ][ 0 ].get_values()
        seq_str = results[ 0 ][ 1 ].get_sequence_str()
        dot_bracket_str = build_dot_bracket( positions )

        return {
            "sequence": seq_str.replace( "T", "U" ),
            "structure": dot_bracket_str
        }

    # Grab 2d coords from viennaRNA
    # There is a python2 wrapper for vienna RNA but not python 3 compatible
    def get_vienna_layout( self, data ):

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

        # return result


class StructureCirclePlotView():
    def __init__( self, structure_id ):
        self.structure_id = structure_id
        self.get_values()

    def get_values( self ):
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
        out = [ ];
        for curr_position in range( 1, len( positions ) + 1 ):
            paired_to_position = positions[ curr_position - 1 ]

            if paired_to_position == 0 or \
                            paired_to_position < curr_position:

                link = None
            else:
                link = paired_to_position - 1

            if link:
                link = int( link )

            out.append( {
                "name": curr_position - 1,
                "link": link,
                "bpp": None if bpps is None else bpps[ curr_position - 1 ]
            } )

        self.data_json = json.dumps( out )


# Generates plaintext structure text files for download
class StructureDownloader():
    def __init__( self, structure_prediction_run_ids, transcript_id ):
        self.structure_prediction_run_ids = structure_prediction_run_ids
        self.transcript_id = transcript_id

    def generate( self ):
        # Fetch the data
        results = database.db_session \
            .query( Structure, StructurePredictionRun, Transcript ) \
            .filter(
                StructurePredictionRun.id == Structure.structure_prediction_run_id,
                Structure.structure_prediction_run_id.in_( self.structure_prediction_run_ids ),
                Structure.transcript_id == self.transcript_id,
                Transcript.id == self.transcript_id
        ) \
            .order_by(
                Structure.structure_prediction_run_id,
                Structure.id
        ) \
            .all()

        return self.generate_txt( results )

    # Generates text using a more compact file format
    def generate_txt( self, results ):
        # first we must extract and display the sequence, using the transcript object. output
        # in fasta-like format
        transcript = results[ 0 ][ 2 ]
        buf = ">" + self.transcript_id + "\n"
        buf += insert_newlines( transcript.get_sequence_str() ) + "\n"

        for result in results:
            structure = result[ 0 ]
            run = result[ 1 ]
            transcript = result[ 2 ]
            positions = structure.get_values()

            # generate and add the header text for this structure
            buf += (
                ">sid_" + str( structure.id ) + "\t" +
                "ENERGY:" + str( structure.energy ) + " kcal/mol\t" +
                run.description + "\n")

            # generate and add dot bracket text
            buf += insert_newlines( build_dot_bracket( positions ) ) + "\n"

        return buf

    # Generates the older and far more cluttered txt format for structures
    def generate_txt_old( self, results ):

        # Generate tab delimited text from the data
        buf = ""
        for result in results:
            structure = result[ 0 ]
            run = result[ 1 ]
            transcript = result[ 2 ]

            seq_str = transcript.get_sequence_str()
            positions = structure.get_values()

            for curr_position in range( 1, len( positions ) + 1 ):
                paired_to_position = positions[ curr_position - 1 ]
                letter = seq_str[ curr_position - 1 ].replace( "T", "U" )

                buf += str( structure.id ) + "\t" + \
                       str( run.description ) + "\t" + \
                       str( structure.transcript_id ) + "\t" + \
                       str( structure.energy ) + "\t" + \
                       str( structure.pc1 ) + "\t" + \
                       str( structure.pc2 ) + "\t" + \
                       str( letter ) + "\t" + \
                       str( curr_position ) + "\t" + \
                       str( paired_to_position ) + "\n"

        return buf


# Generates plain text nucleotide measurements for user download
# Includes raw and normalised
class NucleotideMeasurementDownloader():
    def __init__( self, nucleotide_measurement_run_id, transcript_id ):
        self.nucleotide_measurement_run_id = nucleotide_measurement_run_id
        self.transcript_id = transcript_id

    # Retrieves raw reactivity values and outputs as text
    def get_raw( self ):
        seq_str = Transcript( self.transcript_id ).get_sequence_str()

        # Use the ORM to grab compiled counts
        results = database.db_session \
            .query( RawReactivities ) \
            .filter(
                RawReactivities.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                RawReactivities.transcript_id == self.transcript_id
        ) \
            .all()

        measurement_set = results[ 0 ]
        # minus_unpacked =
        # plus_unpacked = values_str_unpack_int(measurement_set.plus_values)

        cols = [
            values_str_unpack_int( measurement_set.minus_values ),
            values_str_unpack_int( measurement_set.plus_values )
        ]

        # Grab the raw replicate lanes data
        lanes = database.db_session \
            .query( RawReplicateCounts ) \
            .filter(
                RawReplicateCounts.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                RawReplicateCounts.transcript_id == self.transcript_id
        ) \
            .order_by(
                RawReplicateCounts.minusplus_id,
                RawReplicateCounts.bio_replicate_id,
                RawReplicateCounts.tech_replicate_id
        ) \
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
            .filter(
                NucleotideMeasurementSet.nucleotide_measurement_run_id == self.nucleotide_measurement_run_id,
                NucleotideMeasurementSet.transcript_id == self.transcript_id
        ) \
            .all()

        measurement_set = results[ 0 ]
        # TODO detect whether float or int and use the correct unpacker.
        # Needed for raw count values download option
        unpacked = values_str_unpack_float( measurement_set.values )

        # index measurements by pos
        measurements = { }
        for pos in range( 0, len( unpacked ) ):
            value = unpacked[ pos ]
            measurements[ pos + 1 ] = "NA" if value is None else value

        # build the output string
        buf = ""
        n = 0
        for n in range( 0, len( seq_str ) ):
            pos = n + 1
            measurement = "NA" if pos not in measurements else measurements[ pos ]
            buf += str( pos ) + "\t" + \
                   seq_str[ n ] + "\t" + \
                   str( measurement ) + "\n"
            n += 1

        return buf


# Retrieves the BPPM for this transcript_id
class BppmDownloader():
    def fetch( self, transcript_id ):
        import os

        source_filepath = settings.bppms_folder + "/" + transcript_id + ".bppm"

        if not os.path.isfile( source_filepath ):
            return "No BPPM data available for " + transcript_id

        buf = ""
        # Open the raw BPPM and convert to our simpler format
        with open( source_filepath, "r" ) as f:
            first = True
            for line in f:
                if first:  # skip the first line, which shows the length
                    first = False
                    continue

                # add the text for the bppm table
                if "Probability" in line:  # skip header lines
                    continue

                # extract the data, this will be used for structure BPPMs
                bits = line.strip().split( "\t" )
                pos_a = int( bits[ 0 ] )
                pos_b = int( bits[ 1 ] )
                bpp = -float( bits[ 2 ] )

                buf += str( pos_a ) + "\t" + str( pos_b ) + "\t" + str( bpp ) + "\n"
        return buf

        # OLD method - storing in the database is not a good way to do it
        # import zlib, base64
        # # fetch from database
        # results = database.db_session \
        #     .query(Bppm) \
        #     .filter(Bppm.transcript_id==transcript_id) \
        #     .all()
        # bppm = results[0]

        # # decode and return the BPPM
        # decoded = base64.b64decode(bppm.data)
        # data_txt = zlib.decompress(decoded)
        # return data_txt
