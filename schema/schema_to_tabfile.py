import yaml
import yamlordereddictloader
from receptor_utils import simple_bio_seq as simple


schema = yaml.load(open('inferred_gene_submission_schema.yaml', 'r'), Loader=yamlordereddictloader.Loader)

tabfile_data = []
table_descs = []

for table, contents in schema.items():
    table_descs.append({
        'Table': table,
        'Description': contents['description'],
    })

    for fieldname, attributes in contents['properties'].items():
        tabfile_data.append({
            'Table': table,
            'Fieldname': fieldname,
            'Field_type': attributes['type'],
            'Description': attributes['description'] if 'description' in attributes else '',
    })
        
tabfile_data = sorted(tabfile_data, key=lambda x: (x['Table'], x['Fieldname']))
table_descs = sorted(table_descs, key=lambda x: x['Table'])

simple.write_csv('ogrdb_table_descriptions.tab', table_descs, delimiter='\t')
simple.write_csv('ogrdb_table_fields.tab', tabfile_data, delimiter='\t')
