# Usually we'll use the mcodepacket schema from the current Katsu version,
# but in case we need them, other schemas can be listed here:

candigv1_schema = {
    "type": "object",
    "properties": {
        "Patient": {
            "type": "object",
            "properties": {
                "patientId": {
                    "type": "string"
                },
                "gender": {
                    "type": "string"
                },
                "dateOfBirth": {
                    "type": "string"
                },
                "ethnicity": {
                    "type": "string"
                },
                "provinceOfResidence": {
                    "type": "string"
                },
                "dateOfDeath": {
                    "type": "string"
                }
            }
        },
        "Enrollment": {
            "type": "object",
            "properties": {
                "patientId": {
                    "type": "string"
                },
                "ageAtEnrollment": {
                    "type": "string"
                }
            }
        },
        "Diagnosis": {
            "type": "object",
            "properties": {
                "patientId": {
                    "type": "string"
                },
                "diagnosisDate": {
                    "type": "string"
                },
                "cancerType": {
                    "type": "string"
                },
                "histology": {
                    "type": "string"
                },
                "tumorGrade": {
                    "type": "string"
                },
                "specificStage": {
                    "type": "string"
                }
            }
        },
        "Treatment": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "patientId": {
                        "type": "string"
                    },
                    "therapeuticModality": {
                        "type": "string"
                    },
                    "startDate": {
                        "type": "string"
                    },
                    "stopDate": {
                        "type": "string"
                    },
                    "responseToTreatment": {
                        "type": "string"
                    }
                }
            }
        },
        "Outcome": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "patientId": {
                        "type": "string"
                    },
                    "dateOfAssessment": {
                        "type": "string"
                    },
                    "diseaseResponseOrStatus": {
                        "type": "string"
                    },
                    "localId": {
                        "type": "string"
                    },
                    "vitalStatus": {
                        "type": "string"
                    }
                }
            }
        },
        "Sample": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "patientId": {
                        "type": "string"
                    },
                    "sampleId": {
                        "type": "string"
                    },
                    "collectionDate": {
                        "type": "string"
                    },
                    "sampleType": {
                        "type": "string"
                    },
                    "cancerType": {
                        "type": "string"
                    }
                }
            }
        }
    }
}