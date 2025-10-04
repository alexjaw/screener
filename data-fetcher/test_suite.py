"""test_suite.py

Comprehensive test suite for F-Score calculation modules.
This module validates the current implementation and provides regression tests
for future real data fetcher implementations.

The test suite ensures that:
1. Current hardcoded implementation works correctly
2. Future real implementations produce the same results
3. All edge cases and error conditions are handled properly
"""

from models import FinancialData, ParseOptions
import test_data
import fetcher
import parser
import fscore


class TestDataValidation:
    """Test the test data module itself."""
    
    def test_test_companies_list(self):
        """Test that we have the expected test companies."""
        companies = test_data.get_test_companies()
        assert len(companies) == 3
        assert "Intellego Technologies" in companies
        assert "SAAB" in companies
        assert "BioArctic" in companies
    
    def test_company_name_normalization(self):
        """Test company name normalization."""
        assert test_data.normalize_company_name("saab") == "SAAB"
        assert test_data.normalize_company_name("SAAB AB") == "SAAB"
        assert test_data.normalize_company_name("bioarctic b") == "BioArctic"
        
        try:
            test_data.normalize_company_name("unknown company")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
    
    def test_financial_data_structure(self):
        """Test that financial data has correct structure."""
        for company in test_data.get_test_companies():
            data = test_data.get_test_financial_data(company)
            assert isinstance(data, FinancialData)
            assert data.revenue_cur > 0
            assert data.revenue_prev > 0
            assert data.total_assets_cur > 0
            assert data.total_assets_prev > 0


class TestCurrentImplementation:
    """Test the current hardcoded implementation."""
    
    def test_fetcher_returns_correct_data(self):
        """Test that fetcher returns expected data structure."""
        for company in test_data.get_test_companies():
            data = fetcher.fetch_financials(company)
            assert isinstance(data, FinancialData)
            
            # Compare with test data
            expected_data = test_data.get_test_financial_data(company)
            assert data.revenue_cur == expected_data.revenue_cur
            assert data.net_income_cur == expected_data.net_income_cur
            assert data.total_assets_cur == expected_data.total_assets_cur
    
    def test_parser_produces_metrics(self):
        """Test that parser produces all required metrics."""
        for company in test_data.get_test_companies():
            raw_data = fetcher.fetch_financials(company)
            metrics = parser.parse_financials(raw_data)
            
            # Check all required metrics are present
            required_metrics = [
                "roa_positive", "cfo_positive", "roa_improved",
                "accrual_positive", "leverage_decreased", "current_ratio_improved",
                "no_new_shares", "gross_margin_improved", "asset_turnover_improved"
            ]
            for metric in required_metrics:
                assert metric in metrics
                assert isinstance(metrics[metric], bool)
    
    def test_fscore_calculation(self):
        """Test that F-Score calculation produces expected results."""
        expected_scores = test_data.get_expected_f_scores()
        
        for company, expected_score in expected_scores.items():
            actual_score = fscore.score_company(company)
            assert actual_score == expected_score, f"{company}: expected {expected_score}, got {actual_score}"
    
    def test_custom_parse_options(self):
        """Test that custom parse options work correctly."""
        # Test SAAB with absolute leverage (should be different from ratio-based)
        options = ParseOptions(leverage_use_ratio=False)
        score = fscore.score_company("SAAB", options)
        assert isinstance(score, int)
        assert 0 <= score <= 9
        
        # Test BioArctic with share threshold
        options = ParseOptions(share_change_threshold=0.005)
        score = fscore.score_company("BioArctic", options)
        assert isinstance(score, int)
        assert 0 <= score <= 9
    
    def test_custom_options_match_fscore_main(self):
        """Test that custom options match fscore.py main execution."""
        custom_scores = test_data.get_expected_f_scores_custom()
        
        # Test Intellego with asset turnover override
        options = ParseOptions(
            leverage_use_ratio=True,
            share_change_threshold=0.0,
            asset_turnover_override=True,
        )
        score = fscore.score_company("Intellego Technologies", options)
        assert score == custom_scores["Intellego Technologies"]
        
        # Test SAAB with absolute leverage
        options = ParseOptions(
            leverage_use_ratio=False,
            share_change_threshold=0.0,
            asset_turnover_override=None,
        )
        score = fscore.score_company("SAAB", options)
        assert score == custom_scores["SAAB"]
        
        # Test BioArctic with share threshold
        options = ParseOptions(
            leverage_use_ratio=True,
            share_change_threshold=0.005,
            asset_turnover_override=None,
        )
        score = fscore.score_company("BioArctic", options)
        assert score == custom_scores["BioArctic"]


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_unknown_company_fetcher(self):
        """Test that fetcher raises error for unknown companies."""
        try:
            fetcher.fetch_financials("Unknown Company")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
    
    def test_unknown_company_test_data(self):
        """Test that test_data raises error for unknown companies."""
        try:
            test_data.get_test_financial_data("Unknown Company")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
    
    def test_empty_company_name(self):
        """Test handling of empty company names."""
        try:
            fetcher.fetch_financials("")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
        
        try:
            fetcher.fetch_financials("   ")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected


class TestRegressionSuite:
    """Regression tests for future implementations."""
    
    def test_full_pipeline_regression(self):
        """Test the complete pipeline produces consistent results."""
        results = {}
        
        for company in test_data.get_test_companies():
            # Test current implementation
            raw_data = fetcher.fetch_financials(company)
            metrics = parser.parse_financials(raw_data)
            score = fscore.compute_fscore(metrics)
            
            results[company] = {
                "score": score,
                "metrics": metrics,
                "raw_data": raw_data
            }
        
        # Validate against expected scores
        expected_scores = test_data.get_expected_f_scores()
        for company, result in results.items():
            assert result["score"] == expected_scores[company]
    
    def test_data_consistency(self):
        """Test that test data is consistent with fetcher data."""
        for company in test_data.get_test_companies():
            fetcher_data = fetcher.fetch_financials(company)
            test_data_result = test_data.get_test_financial_data(company)
            
            # All fields should match exactly
            for field in fetcher_data.__dataclass_fields__:
                assert getattr(fetcher_data, field) == getattr(test_data_result, field)


def run_manual_tests():
    """Run manual tests without pytest framework."""
    print("🧪 Running F-Score Test Suite...")
    
    # Test data validation
    print("\n📊 Testing data validation...")
    companies = test_data.get_test_companies()
    print(f"✅ Test companies: {companies}")
    
    expected_scores = test_data.get_expected_f_scores()
    print(f"✅ Expected F-Scores: {expected_scores}")
    
    # Test current implementation
    print("\n🔧 Testing current implementation...")
    for company in companies:
        try:
            score = fscore.score_company(company)
            expected = expected_scores[company]
            status = "✅" if score == expected else "❌"
            print(f"{status} {company}: {score}/9 (expected {expected})")
        except Exception as e:
            print(f"❌ {company}: Error - {e}")
    
    # Test custom options
    print("\n⚙️ Testing custom options...")
    try:
        options = ParseOptions(leverage_use_ratio=False)
        score = fscore.score_company("SAAB", options)
        print(f"✅ SAAB with absolute leverage: {score}/9")
    except Exception as e:
        print(f"❌ Custom options test failed: {e}")
    
    # Test error handling
    print("\n🚨 Testing error handling...")
    try:
        fetcher.fetch_financials("Unknown Company")
        print("❌ Should have raised ValueError")
    except ValueError:
        print("✅ Correctly raises ValueError for unknown company")
    
    print("\n🎉 Test suite completed!")


def run_unit_tests():
    """Run unit tests without pytest framework."""
    print("🧪 Running Unit Tests...")
    
    test_classes = [
        TestDataValidation(),
        TestCurrentImplementation(), 
        TestErrorHandling(),
        TestRegressionSuite()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📋 Running {class_name}...")
        
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    method = getattr(test_class, method_name)
                    method()
                    print(f"  ✅ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"  ❌ {method_name}: {e}")
    
    print(f"\n📊 Test Results: {passed_tests}/{total_tests} passed")
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed!")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    print("🚀 F-Score Test Suite")
    print("=" * 50)
    
    # Run manual tests first
    run_manual_tests()
    
    print("\n" + "=" * 50)
    
    # Run unit tests
    success = run_unit_tests()
    
    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed - check output above")
        exit(1)
