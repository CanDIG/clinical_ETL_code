import os
import sys
# Include src/ directory in the module search path.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(os.sep.join([grandparent_dir, "src"]))
import clinical_etl.mappings as mappings

def map_primary_site(data_values):
    """Converts ICD-O codes into textual body locations, consistent with the schema's PrimarySiteEnum.
    Args: 
        data_values: values dict with single pipe-delimited string, e.g. "a|b|c"
    Returns:
        a list of strings e.g. ["Skin","Lip","Gum"]
    """
    ICDO_dict = {
        'C31': 'Accessory sinuses',
        'C74': 'Adrenal gland',
        'C21': 'Anus and anal canal',
        'C01': 'Base of tongue',
        'C67': 'Bladder',
        'C40': 'Bones, joints and articular cartilage of limbs',
        'C41': 'Bones, joints and articular cartilage of other and unspecified sites',
        'C71': 'Brain',
        'C50': 'Breast',
        'C34': 'Bronchus and lung',
        'C53': 'Cervix uteri',
        'C18': 'Colon',
        'C49': 'Connective, subcutaneous and other soft tissues',
        'C54': 'Corpus uteri',
        'C15': 'Esophagus',
        'C69': 'Eye and adnexa',
        'C04': 'Floor of mouth',
        'C23': 'Gallbladder',
        'C03': 'Gum',
        'C38': 'Heart, mediastinum, and pleura',
        'C42': 'Hematopoietic and reticuloendothelial systems',
        'C13': 'Hypopharynx',
        'C64': 'Kidney',
        'C32': 'Larynx',
        'C00': 'Lip',
        'C22': 'Liver and intrahepatic bile ducts',
        'C77': 'Lymph nodes',
        'C70': 'Meninges',
        'C30': 'Nasal cavity and middle ear',
        'C11': 'Nasopharynx',
        'C10': 'Oropharynx',
        'C26': 'Other and ill-defined digestive organs',
        'C76': 'Other and ill-defined sites',
        'C14': 'Other and ill-defined sites in lip oral cavity and pharynx',
        'C39': 'Other and ill-defined sites within respiratory system and intrathoracic organs',
        'C57': 'Other and unspecified female genital organs',
        'C08': 'Other and unspecified major salivary glands',
        'C63': 'Other and unspecified male genital organs',
        'C24': 'Other and unspecified parts of biliary tract',
        'C06': 'Other and unspecified parts of mouth',
        'C02': 'Other and unspecified parts of tongue',
        'C68': 'Other and unspecified urinary organs',
        'C75': 'Other endocrine glands and related structures',
        'C56': 'Ovary',
        'C05': 'Palate',
        'C25': 'Pancreas',
        'C07': 'Parotid gland',
        'C60': 'Penis',
        'C47': 'Peripheral nerves and autonomic nervous system',
        'C58': 'Placenta',
        'C61': 'Prostate gland',
        'C12': 'Pyriform sinus',
        'C19': 'Rectosigmoid junction',
        'C20': 'Rectum',
        'C65': 'Renal pelvis',
        'C48': 'Retroperitoneum and peritoneum',
        'C44': 'Skin',
        'C17': 'Small intestine',
        'C72': 'Spinal cord, cranial nerves,and other parts of the nervous system',
        'C16': 'Stomach',
        'C62': 'Testis',
        'C37': 'Thymus',
        'C73': 'Thyroid gland',
        'C09': 'Tonsil',
        'C33': 'Trachea',
        'C66': 'Ureter',
        'C66': 'Uterus, NOS',
        'C52': 'Vagina',
        'C51': 'Vulva',
        'C80': 'Unknown primary site',
    }
    # Check for Null input
    mapping_vals = mappings.pipe_delim(data_values)
    if mapping_vals is None:
        return None
    if len(mapping_vals) == 0:
        return None
    result = []
    for mapping_val in mapping_vals:
        if mapping_val in ICDO_dict:
            result.append(ICDO_dict[mapping_val])
    return result
