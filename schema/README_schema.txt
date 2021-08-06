The YAML schema is used to build most of the SQLAlchemy object definitions, and also controls various aspects of the
UI:

- Each property has a description, which is generally surfaced as hover-over help
- The label field defines a text label which is used for the property in views and edit screens
- The following properties control various aspects of the UI:
    readonly - Display the property as a non-editable field in edit screens
    tableview - If true, include the property in tabular views of the object class
    hide - If true, don't include the property in view or edit screens
    private - only display to admin users


build_from_schema.py is used to generate many of the database, form and template files. All generated files have
a note at the top saying that they have been automatically generated. They should only be modified by changing the
schema definition. The usual build cycle is:

<modify inferred_gene_submission_schema.yaml>
run build_from_schema.py
flask db migrate
flask db upgrade
