# OGRDB API v2.0.0 Guide

The Open Germline Receptor Database (OGRDB) API v2.0.0 provides programmatic access to immunoglobulin and T-cell receptor germline gene sequences and sets. This guide explains the capabilities of the API and provides examples of its use.

## Introduction

The OGRDB API v2.0.0 is a REST API that follows the OpenAPI 3.1.0 specification. It provides access to germline sequence data in various formats and allows you to:

- Get service information
- List available species
- List available germline sets for a species
- Download specific germline sets in different formats
- List available versions of a germline set

## Base URL

All API requests should be made to:

```
https://ogrdb.airr-community.org/api_v2
```

## Endpoints

### Service Status

Check if the service is running:

```
GET /
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/
```

Response:

```json
{
  "result": "Service is up"
}
```

### Service Information

Get information about the API service:

```
GET /info
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/info
```

Response includes information about the API version, supported features, and schema details.

### List Available Species

Get a list of all species for which germline sets are available:

```
GET /germline/species
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/germline/species
```

Response:

```json
{
  "species": [
    {
      "id": "NCBITAXON:9606",
      "label": "Homo sapiens"
    },
    {
      "id": "NCBITAXON:10090",
      "label": "Mus musculus"
    }
  ]
}
```

### List Germline Sets for a Species

Get available germline sets for a specific species:

```
GET /germline/sets/{species_id}
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/germline/sets/NCBITAXON:9606
```

Response:

```json
{
  "germline_species": [
    {
      "germline_set_id": "1",
      "germline_set_name": "Human_IGH",
      "species": {
        "id": "NCBITAXON:9606",
        "label": "Homo sapiens"
      },
      "species_subgroup": null,
      "species_subgroup_type": null,
      "locus": "IGH"
    },
    {
      "germline_set_id": "2",
      "germline_set_name": "Human_IGK",
      "species": {
        "id": "NCBITAXON:9606",
        "label": "Homo sapiens"
      },
      "species_subgroup": null,
      "species_subgroup_type": null,
      "locus": "IGK"
    }
  ]
}
```

### Get a Specific Germline Set

Retrieve a specific germline set by ID and version:

```
GET /germline/set/{germline_set_id}/{release_version}
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/germline/set/1/2.0
```

Response:

```json
{
  "Info": {
    "title": "Human IGH Germline Set",
    "version": "2.0"
  },
  "GermlineSet": [
    {
      "germline_set_id": "1",
      "author": "Author Name",
      "lab_name": "Lab Name",
      "lab_address": "Lab Address",
      "release_version": 2.0,
      "release_description": "Updated germline set",
      "release_date": "2025-01-15",
      "germline_set_name": "Human_IGH",
      "germline_set_ref": "OGRDB:Human_IGH:2.0",
      "species": {
        "id": "NCBITAXON:9606",
        "label": "Homo sapiens"
      },
      "locus": "IGH",
      "allele_descriptions": [
        // Array of allele descriptions
      ]
    }
  ]
}
```

### Get a Germline Set in a Specific Format

Retrieve a germline set in a specific format (e.g., FASTA):

```
GET /germline/set/{germline_set_id}/{release_version}/{format}
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/germline/set/1/2.0/fasta
```

Response: A text file containing the sequences in FASTA format.

### List All Versions of a Germline Set

Get all available versions of a specific germline set:

```
GET /germline/set/{germline_set_id}/versions
```

Example:

```bash
curl https://ogrdb.airr-community.org/api_v2/germline/set/1/versions
```

Response:

```json
{
  "versions": [1.0, 1.5, 2.0]
}
```

## Format Options

When requesting a germline set in a specific format, the following options are available:

- `fasta`: Standard FASTA format
- gapped: FASTA format with IMGT-gapped sequences
- `ungapped`: FASTA format with ungapped sequences
- `airr`: AIRR-compliant format

## Using Germline Set Identifiers

Germline sets in the API v2.0.0 are identified by unique IDs and versions. Each germline set has:

1. A unique `germline_set_id`
2. A `release_version` number
3. A standardized reference (`germline_set_ref`) in the form "OGRDB:Name:Version"

## Error Handling

The API returns appropriate HTTP status codes:

- 200: Successful request
- 400: Invalid request (with error details)
- 500: Server error (with error details)

Error responses include a message field explaining the error:

```json
{
  "message": "Germline set not found"
}
```

## Differences from v1 API

The v2.0.0 API includes several enhancements over the previous version:

1. **Standardized Identifiers**: Uses NCBI Taxonomy IDs for species
2. **Ontology Support**: Species are represented as ontology objects with ID and label
3. **Improved Error Handling**: Consistent error responses
4. **Version Management**: Better support for listing and accessing specific versions
5. **Rich Metadata**: More detailed information about each germline set
6. **AIRR Community Alignment**: Follows AIRR Community standards

## Conclusion

The OGRDB API v2.0.0 provides comprehensive access to germline sequence data with improved organization and standardization. Whether you're building tools for immunogenetics research or integrating germline data into your applications, this API offers a reliable and structured way to access the latest germline sequence information.

For further assistance or to report issues, please contact the AIRR Community at join@airr-community.org.