
scan_branch_schema = {
    'type': 'object',
    'properties': {
        'branch_id': {'type': 'integer'}
    }, 
    'required': ['branch_id']
}

details_false_positive = {
    'type': 'object',
    'properties': {
        'vuln_id': {'type': 'integer'},
        'checked': {'type': 'boolean'}
    },
    'required': ['vuln_id', 'checked']
}

details_printPDF = {
    'type': 'object',
    'properties': {
        'scan_id' : {'type': 'integer'}
    },
    'required': ['scan_id']
}
