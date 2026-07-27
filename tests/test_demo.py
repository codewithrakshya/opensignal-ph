from opensignal.demo import run_portfolio_demo


def test_portfolio_demo_runs_end_to_end(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        """[{
          "document_id": "demo-source",
          "title": "DRUG A EVENT X surveillance",
          "publisher": "FDA",
          "url": "https://www.fda.gov/example",
          "content": "DRUG A EVENT X reports require expert review."
        }]"""
    )
    result = run_portfolio_demo(tmp_path / "data", evidence)
    assert result.curated_rows > 0
    assert result.statistical_scores == 8
    assert result.temporal_scores == 16
    assert result.brief_status == "generated"
