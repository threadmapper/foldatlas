live = False

app_base_url = ''

if live:
    # app_base_url = "http://www.foldatlas.com/"  # if this is wrong, some ajax will fail
    static_base_url = "/static"
    static_path = "/var/www/foldatlas/static"
    dbuser = "root"
    dbpassword = "{{ mysql_root_password }}"
    bppms_folder = "/var/www/bppms"  # this will need to be changed for live site

    sqlalchemy_track_modifications = False
    sqlalchemy_echo = False
else:
    # app_base_url = "http://localhost:8080"
    static_base_url = "/static"
    static_path = "/var/www/static"
    dbuser = "fa_user"
    dbpassword = "{{ foldatlas_db_pass }}"
    bppms_folder = "/var/www/bppms"

    sqlalchemy_track_modifications = True  # incurs overhead: only for dev
    sqlalchemy_echo = True

db_name = "foldatlas"

# Format the database connection string
database_uri = "mysql+mysqlconnector://{}:{}@127.0.0.1/{}?{}".format( dbuser,
                                                                      dbpassword,
                                                                      db_name,
                                                                      'charset=utf8&use_unicode=1' )

# Points to the general data folder
data_folder = "/var/www/source_data"

# Points to structure data folder, which contains a *lot* of files
structure_data_folder = "/var/www/structure_data"
structure_tids_filepath = data_folder + "/structure_tids.txt"


class ExperimentIds( object ):
    def __init__( self,
                  strain_id,
                  nucleotide_measurement_run_id,
                  in_silico_structure_prediction_run_id,
                  in_vivo_structure_prediction_run_id ):
        """ Store the ids for an experiment """

        self.strain_id = strain_id  # e.g. Col_0

        # Basically a synonym for 'experiment id'
        self.nucleotide_measurement_run_id = nucleotide_measurement_run_id

        self.in_silico_structure_prediction_run_id = in_silico_structure_prediction_run_id
        self.in_vivo_structure_prediction_run_id = in_vivo_structure_prediction_run_id

    @property
    def structure_prediction_run_ids(self):
        return [ self.in_silico_structure_prediction_run_id,
                 self.in_vivo_structure_prediction_run_id ]


# # Experimental data for the first FoldAtlas dataset # #

v1_ids = ExperimentIds( strain_id='Col_0',
                        nucleotide_measurement_run_id=1,
                        in_silico_structure_prediction_run_id=1,
                        in_vivo_structure_prediction_run_id=2 )

raw_replicate_counts_keys = {
    "minus": [ [ "mDMS_1_ATCACG_L001_R1" ],
               [ "mDMS_2_TAGCTT_L001_R1" ],
               [ "mDMS_3_CGATGT_L001_R1" ]
               ],
    "plus": [ [ "pDMS_1_ACAGTG_L001_R1" ],
              [ "pDMS_2_CTTGTA_L001_R1" ],
              [ "pDMS_3_TTAGGC_L001_R1" ]
              ]
}

dms_reactivities_experiment = {
    "nucleotide_measurement_run_id": 1,
    "strain_id": "Col_0",
    "nucleotides_filepath": data_folder + "/a_thaliana_compiled_counts.txt",
    "description": "DMS reactivities"
}

ribosome_profile_experiment = {
    "nucleotide_measurement_run_id": 2,
    "strain_id": "Col_0",
    "nucleotides_filepath": data_folder + "/p_site_counts_all.txt",
    "description": "Ribosome occupancies",
}

structures_in_silico = {
    "structure_prediction_run_id": 1,
    "strain_id": "Col_0",
    "description": "In silico structure prediction",
    "source_filepath": structure_data_folder + "/in_silico_structures",
    "source_ext": ".ct",
}

structures_in_vivo = {
    "structure_prediction_run_id": 2,
    "strain_id": "Col_0",
    "description": "In vivo experimental structure prediction",
    "source_filepath": structure_data_folder + "/in_vivo_structures",
    "source_ext": ".ct",
}

transcripts_fasta_filepath = data_folder + "/transcripts.fasta"

base_path = "/var/www/foldatlas"

genoverse_base = static_base_url + "/genoverse"

# path of folder for temporary files
temp_folder = "/tmp"

# Strain metadata. This is used to parse from source files when hydrating the DB.
strains = [
    {
        "name": "Col_0",
        "description": "TAIR 10 Columbia reference ecotype",
        "sequence_filename": "TAIR10_combined.fas",
        "annotation_filename": "consolidated_annotation.Col_0.gff3"
    }  # ,

    # {
    #     "name": "Bur_0",
    #     "description": "Bur_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "bur_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Bur_0.gff3"
    # }, {
    #     "name": "Can_0",
    #     "description": "Can_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "can_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Can_0.gff3"
    # }

    # comment these out for the real thing
    # , {
    #     "name": "Ct_1",
    #     "description": "Ct_1 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "ct_1.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Ct_1.gff3"
    # }, {
    #     "name": "Edi_0",
    #     "description": "Edi_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "edi_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Edi_0.gff3"
    # }, {
    #     "name": "Hi_0",
    #     "description": "Hi_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "hi_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Hi_0.gff3"
    # }, {
    #     "name": "Kn_0",
    #     "description": "Kn_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "kn_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Kn_0.gff3"
    # }, {
    #     "name": "Ler_0",
    #     "description": "Ler_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "ler_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Ler_0.gff3"
    # }, {
    #     "name": "Mt_0",
    #     "description": "Mt_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "mt_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Mt_0.gff3"
    # }, {
    #     "name": "No_0",
    #     "description": "No_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "no_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.No_0.gff3"
    # }, {
    #     "name": "Oy_0",
    #     "description": "Oy_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "oy_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Oy_0.gff3"
    # }, {
    #     "name": "Po_0",
    #     "description": "Po_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "po_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Po_0.gff3"
    # }, {
    #     "name": "Rsch_4",
    #     "description": "Rsch_4 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "rsch_4.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Rsch_4.gff3"
    # }, {
    #     "name": "Sf_2",
    #     "description": "Sf_2 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "sf_2.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Sf_2.gff3"
    # }, {
    #     "name": "Tsu_0",
    #     "description": "Tsu_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "tsu_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Tsu_0.gff3"
    # }, {
    #     "name": "Wil_2",
    #     "description": "Wil_2 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "wil_2.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Wil_2.gff3"
    # }, {
    #     "name": "Ws_0",
    #     "description": "Ws_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "ws_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Ws_0.gff3"
    # }, {
    #     "name": "Wu_0",
    #     "description": "Wu_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "wu_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Wu_0.gff3"
    # }, {
    #     "name": "Zu_0",
    #     "description": "Zu_0 strain, sequenced by the 19 Genomes project",
    #     "sequence_filename": "zu_0.v7.PR_in_lowercase.fas",
    #     "annotation_filename": "consolidated_annotation.Zu_0.gff3"
    # }

]

ignored_chromosomes = { "chloroplast", "mitochondria" }
