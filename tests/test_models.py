from customer_discovery.models.company import CompanyRecord, company_json_schema


def test_make_id_from_domain():
    rid = CompanyRecord.make_id("Foo", "https://www.foo.io")
    assert rid == "foo-io"


def test_json_schema_has_required_fields():
    schema = company_json_schema()
    assert "CompanyRecord" in schema.get("$defs", {}) or "properties" in schema
