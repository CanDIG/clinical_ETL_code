#!/usr/bin/env python
# coding: utf-8
import mappings


# Vital signs are saved in a dict for extra properties
def vital_signs_node(mapping):
    vital_signs = {
        'WEIGHT_BEFORE_STD': 'weight_before_illness',
        'WEIGHT_BEFORE_STD_UN': 'weight_before_illness_unit',
        'WEIGHT_25_AGE_STD': 'weight_around_25',
        'WEIGHT_25_AGE_STD_UN': 'weight_around_25_unit',
        'HEIGHT_STD': 'height',
        'HEIGHT_STD_UN': 'height_unit'
    }
    new_dict = {}
    for item in mapping.keys():
        if item in mapping:
            new_dict[vital_signs[item]] = mapping[item]
    return new_dict


# Several different codes from the COMPARISON dataset map to rac
def race_node(mapping):
    race_mapping_dict = {
        'RACE3': 'white',
        'RACE2': 'white',
        'RACE10': 'black or african american',
        'RACE97': 'american indian or alaska native',
        'RACE98': 'asian',
        'RACE99': 'native hawaiian or pacific islander'
    }
    # for each possible race
    result = ""
    for list_item in mapping.keys():
        item = mappings.single_val({list_item: mapping[list_item]})
        # check if value marked as '1' or possibly name of race written
        if item == '1':
            result = race_mapping_dict[list_item]
    if result == "nan":
        result = None
    return result


# Vital signs are saved in a dict for extra properties
def tumor_marker_node(mapping):
    tumor_marker_list = []
    subject = mappings.single_val({'Subject': mapping['Subject']})
    tmv = mappings.list_val({'CEA_VAL': mapping['CEA_VAL']})
    for i in range(0, len(tmv)):
        tumor_marker_dict = {
            "individual": subject,
            "id": f"{subject}-tm-{i}",
            "tumor_marker_data_value": {}
        }
        tumor_marker_dict["tumor_marker_data_value"]["value"] = {
            "value": tmv[i],
            "comparator": "="
        }

        # lab results go in extra_properties
        lab_results = {
            'GLUC_VAL_RAW': 'glucose',
            'GLUC_VAL_UN': 'glucose_unit',
            'NA_VAL_RAW': 'sodium',
            'NA_VAL_UN': 'sodium_unit',
            'K_VAL_RAW': 'potassium',
            'K_VAL_UN': 'potassium_unit',
            'CL_VAL_RAW': 'chloride',
            'CL_VAL_UN': 'chloride_unit',
            'S_CREAT_VAL_RAW': 'serum_creatinine',
            'S_CREAT_VAL_UN': 'serum_creatinine_unit',
            'CA_VAL_RAW': 'calcium',
            'CA_VAL_UN': 'calcium_unit',
            'MG_VAL_RAW': 'magnesium',
            'MG_VAL_UN': 'magnesium_unit',
            'AST_VAL_RAW': 'aspartate_aminotransferase_sgot',
            'AST_VAL_UN': 'aspartate_aminotransferase_sgot_unit',
            'BICARB_VAL_RAW': 'bicarbonate',
            'BICARB_VAL_UN': 'bicarbonate_unit',
            'BUN_VAL_RAW': 'blood_uria_nitrogen',
            'BUN_VAL_UN': 'blood_urea_nitrogen_unit',
            'T_BILI_VAL_RAW': 'total_bilirubin',
            'T_BILI_VAL_UN': 'total_bilirubin_unit',
            'TPROT_VAL_RAW': 'total_protein',
            'TPROT_VAL_UN': 'total_protein_unit',
            'ALB_VAL_RAW': 'albumin',
            'ALB_VAL_UN': 'albumin_unit',
            'PHOS_VAL_RAW': 'phosphate',
            'PHOS_VAL_UN': 'phosphate_unit',
            'ALT_VAL_RAW': 'alt_sgpt',
            'ALT_VAL_UN': 'alt_sgpt_unit',
            'ALKPHOS_VAL_RAW': 'alp_alkaline_phosphatase',
            'ALKPHOS_VAL_UN': 'alp_alkaline_phosphatase_unit',
            'LDH_VAL_RAW': 'lactate_dehydrogenase',
            'LDH_VAL_UN': 'lactate_dehydrogenase_unit',
            'HGB_VAL_RAW': 'hemoglobin',
            'HGB_VAL_UN': 'hemoglobin_unit',
            'WBC_VAL_RAW': 'leukocytes_wbc',
            'WBC_VAL_UN': 'leukocytes_wbc_unit',
            'PLT_VAL_RAW': 'platelets',
            'PLT_VAL_UN': 'platelets_unit',
            'NEUT_VAL_RAW': 'neutrophils',
            'NEUT_VAL_UN': 'neutrophils_unit',
            'LYMP_VAL_RAW': 'lymphocytes',
            'LYMP_VAL_UN': 'lymphocytes_unit',
            'MONO_VAL_RAW': 'monocytes',
            'MONO_VAL_UN': 'monocytes_unit',
            'EOSI_VAL_RAW': 'eosinophils',
            'EOSI_VAL_UN': 'eosinophils_unit',
            'BASO_VA_RAW': 'basophils',
            'BASO_VA_UN': 'basophils_unit'
        }
        new_dict = {}
        for item in lab_results.keys():
            if item in mapping:
                new_dict[lab_results[item]] = mappings.single_val({item: mapping[item]})
        tumor_marker_dict["extra_properties"] = new_dict
        tumor_marker_list.append(tumor_marker_dict)

    return tumor_marker_list


def genetic_specimen_node(mapping):
    ##genomics_report.genetic_specimen.0.id*,
    ##"genomics_report.genetic_specimen.0.collection_body+",COLLEC_TIMEPOINT
    ##genomics_report.genetic_specimen.0.laterality,
    ##genomics_report.genetic_specimen.0.specimen_type*+,BLOOD_TYPE
    genetic_specimen_list = []

    coll_body = mappings.list_val({'COLLEC_TIMEPOINT': mapping['COLLEC_TIMEPOINT']})
    blood_type = mappings.list_val({'BLOOD_TYPE': mapping['BLOOD_TYPE']})
    subject = mappings.single_val({'Subject': mapping['Subject']})

    if len(coll_body) != len(blood_type):
        raise SyntaxError(f"For sample {subject}, there are {len(coll_body)} COLLEC_TIMEPOINT but {len(blood_type)} BLOOD_TYPE")
    for i in range(0, len(coll_body)):
        genetic_specimen_dict = {
            "id": f"{subject}-gs-{i}",
            "collection_body": coll_body[i]
        }

        # ontology search for specimen_type
        genetic_specimen_dict["specimen_type"] = f"ontology:{blood_type[i]}"
        genetic_specimen_list.append(genetic_specimen_dict)
    return genetic_specimen_list


# "genomics_report.genetic_variant.id*",
# "genomics_report.genetic_variant.data_value+",MUT_STAT
# "genomics_report.genetic_variant.gene_studied.0",GENE_MUT ##A gene targeted for mutation analysis,
#     identified in HUGO Gene Nomenclature Committee (HGNC) notation.
def genetic_variant_node(mapping):  # genetic_variant_node(Subject,MUT_STAT,GENE_MUT)
    subject = mappings.single_val({'Subject': mapping['Subject']})
    genetic_variant_dict = {
        "id": subject
    }

    mut_stat = mappings.single_val({'MUT_STAT': mapping['MUT_STAT']})
    if mut_stat == "Present" or mut_stat == "Positive":
        genetic_variant_dict["data_value"] = {
            "id": "LOINC:LA9633-4",
            "label": "Present"
        }
    elif mut_stat == "Absent" or mut_stat == "Negative":
        genetic_variant_dict["data_value"] = {
            "id": "LOINC:LA9634-2",
            "label": "Absent"
        }
    else:
        genetic_variant_dict["data_value"] = {
            "id": "LOINC:LA18198-4",
            "label": "No call"
        }

    gene_mut = mappings.list_val({'GENE_MUT': mapping['GENE_MUT']})
    genetic_variant_dict["gene_studied"] = []
    for i in range(0, len(gene_mut)):
        if gene_mut[i] != "nan" and gene_mut[i] != '':
            genetic_variant_dict["gene_studied"].append(f"ontology:hgnc_api {gene_mut[i]}")
            # gene_dict = {}
            # gene = hgnc_api(gene_mut[i].split(" ")[0])
            # if "response" in gene:
            #     if len(gene["response"]["docs"]) > 0:
            #         gene_dict["id"] = gene["response"]["docs"][0]["hgnc_id"]
            #         gene_dict["label"] = gene_mut[i]
            #         genetic_variant_dict["gene_studied"].append(gene_dict)
            # else:
            #     raise ValueError(f"Gene {gene_mut[i]} not found in HGNC")

    return genetic_variant_dict
