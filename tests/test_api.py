def test_service_info_response_has_expected_fields(test_client):
    response = test_client.get("/api_v2/info")

    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "OGRDB API"
    assert data["version"] == "2.0.0"
    assert data["api"]["title"] == "OGRDB API Detailed"


def test_germline_species_empty_response(test_client):
    response = test_client.get("/api_v2/germline/species")

    assert response.status_code == 200
    assert response.get_json() == {"species": []}


def test_germline_species_and_sets_response_schema(test_client, published_records):
    species_response = test_client.get("/api_v2/germline/species")
    assert species_response.status_code == 200
    assert species_response.get_json() == {
        "species": [{"id": "9606", "label": published_records["species"]}]
    }

    sets_response = test_client.get("/api_v2/germline/sets/9606")
    assert sets_response.status_code == 200
    assert sets_response.get_json() == {
        "germline_species": [
            {
                "germline_set_id": published_records["api_germline_set_id"],
                "germline_set_name": published_records["germline_set_name"],
                "species": {"id": "9606", "label": published_records["species"]},
                "species_subgroup": None,
                "species_subgroup_type": "none",
                "locus": "IGH",
            }
        ]
    }


def test_legacy_germline_routes_return_species_sets_and_versions(
    test_client, published_records
):
    species_response = test_client.get("/api/germline/species")
    assert species_response.status_code == 200
    assert published_records["species"] in species_response.get_json()["species"]

    sets_response = test_client.get("/api/germline/sets/Homo%20sapiens")
    assert sets_response.status_code == 200
    assert sets_response.get_json()[0]["germline_set_id"] == "GTEST01"

    versions_response = test_client.get("/api/germline/versions/GTEST01")
    assert versions_response.status_code == 200
    assert versions_response.get_json()[0]["release_version"] == 1
    assert versions_response.get_json()[0]["status"] == "published"


def test_germline_versions_and_versioned_fasta_download(
    test_client, published_records
):
    versions_response = test_client.get(
        f"/api_v2/germline/set/{published_records['api_germline_set_id']}/versions"
    )
    assert versions_response.status_code == 200
    assert versions_response.get_json() == {"versions": [1]}

    download_response = test_client.get(
        f"/api_v2/germline/set/{published_records['api_germline_set_id']}/1/ungapped"
    )
    assert download_response.status_code == 200
    assert download_response.headers["Content-Disposition"].startswith("attachment;")
    assert download_response.get_data(as_text=True) == (
        f">{published_records['gene_name']}*00\nACGTACGT\n"
    )


def test_germline_api_rejects_unknown_species_and_format(
    test_client, published_records
):
    unknown_species = test_client.get("/api_v2/germline/sets/999999")
    assert unknown_species.status_code == 400
    assert unknown_species.get_json() == {"message": "Invalid species ID"}

    invalid_format = test_client.get(
        f"/api_v2/germline/set/{published_records['api_germline_set_id']}/1/invalid"
    )
    assert invalid_format.status_code == 400
    assert invalid_format.get_json() == {"error": "invalid format specified"}
