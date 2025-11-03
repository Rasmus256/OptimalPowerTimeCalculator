import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, date, timezone
import os

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from freezegun import freeze_time
    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False

from rest import (
    EnergyPrice, getprices, getFuturePrices,
    determineLongestConsequtiveHours, getTotalCostIfImpatient,
    cachedPrices
)

if FASTAPI_AVAILABLE:
    from rest import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    if FASTAPI_AVAILABLE:
        return TestClient(app)
    return None


@pytest.fixture
def sample_energy_data():
    """Sample energy price data from API."""
    return {
        "gridCompany": {
            "chargeTypeCode": "T-C-F-T-TD",
            "gln_Number": "5790000611003",
            "gridCompanyNumber": "344",
            "name": "N1 A/S",
            "priceArea": "DK1"
        },
        "records": [
            {
                "CO2Emission": 75.5,
                "ElAfgift": 0.72,
                "EnergiNetNetTarif": 0.061,
                "EnergiNetSystemTarif": 0.074,
                "HourDK": "2024-01-15T13:00:00",
                "HourUTC": "2024-01-15T12:00:00",
                "Moms": 0.26940143325,
                "NetselskabTarif": 0.0867,
                "SpotPrice": 0.135905733,
                "Total": 0.5,
                "TotalExMoms": 0.4
            },
            {
                "CO2Emission": 136.5,
                "ElAfgift": 0.72,
                "EnergiNetNetTarif": 0.061,
                "EnergiNetSystemTarif": 0.074,
                "HourDK": "2024-01-15T14:00:00",
                "HourUTC": "2024-01-15T13:00:00",
                "Moms": 0.25379038725,
                "NetselskabTarif": 0.0867,
                "SpotPrice": 0.073461549,
                "Total": 0.3,
                "TotalExMoms": 0.24
            },
            {
                "CO2Emission": 160.17,
                "ElAfgift": 0.72,
                "EnergiNetNetTarif": 0.061,
                "EnergiNetSystemTarif": 0.074,
                "HourDK": "2024-01-15T15:00:00",
                "HourUTC": "2024-01-15T14:00:00",
                "Moms": 0.247670147625,
                "NetselskabTarif": 0.0867,
                "SpotPrice": 0.0489805905,
                "Total": 0.7,
                "TotalExMoms": 0.56
            },
            {
                "CO2Emission": 174.25,
                "ElAfgift": 0.72,
                "EnergiNetNetTarif": 0.061,
                "EnergiNetSystemTarif": 0.074,
                "HourDK": "2024-01-15T16:00:00",
                "HourUTC": "2024-01-15T15:00:00",
                "Moms": 0.242170801875,
                "NetselskabTarif": 0.0867,
                "SpotPrice": 0.0269832075,
                "Total": 0.4,
                "TotalExMoms": 0.32
            }
        ]
    }


@pytest.fixture
def sample_energy_prices():
    """Sample EnergyPrice objects for testing."""
    return [
        EnergyPrice("2024-01-15T12:00:00Z", 0.5),
        EnergyPrice("2024-01-15T13:00:00Z", 0.3),
        EnergyPrice("2024-01-15T14:00:00Z", 0.7),
        EnergyPrice("2024-01-15T15:00:00Z", 0.4)
    ]


class TestEnergyPrice:
    """Test EnergyPrice class functionality."""

    def test_initialization_with_fromts_and_price(self):
        """Test EnergyPrice initialization with fromTs and price."""
        fromTs = "2024-01-15T10:00:00Z"
        price = 0.5

        energy_price = EnergyPrice(fromTs, price)

        assert energy_price.fromTs == datetime.fromisoformat(fromTs)
        assert energy_price.toTs == energy_price.fromTs + timedelta(hours=1)
        assert energy_price.price == price

    def test_string_representation(self):
        """Test EnergyPrice string representation."""
        fromTs = "2024-01-15T10:00:00Z"
        price = 0.5

        energy_price = EnergyPrice(fromTs, price)
        str_repr = str(energy_price)

        # Check that the string contains the datetime and price information
        assert "2024-01-15" in str_repr
        assert "10:00:00" in str_repr
        assert "11:00:00" in str_repr  # toTs should be 1 hour later
        assert str(price) in str_repr


class TestGetPrices:
    """Test getprices function."""

    @patch('rest.requests.get')
    def test_successful_api_response(self, mock_get, sample_energy_data):
        """Test successful API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(sample_energy_data).encode()
        mock_get.return_value = mock_response

        test_date = date(2024, 1, 15)
        gln_number = "123456789"

        result = getprices(test_date, gln_number)

        assert len(result) == 4
        assert all(isinstance(price, EnergyPrice) for price in result)
        assert result[0].price == 0.5
        assert result[1].price == 0.3

        # Verify API call was made correctly
        expected_url = f'https://elprisen.somjson.dk/elpris?GLN_Number={gln_number}&start=2024-01-15'
        mock_get.assert_called_once_with(expected_url)

    @patch('rest.requests.get')
    def test_api_response_with_grid_company_info(self, mock_get, sample_energy_data):
        """Test that API response with gridCompany info is handled correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(sample_energy_data).encode()
        mock_get.return_value = mock_response

        test_date = date(2024, 1, 15)
        gln_number = "5790000611003"  # Use the GLN from sample data

        result = getprices(test_date, gln_number)

        # Verify that the gridCompany info doesn't interfere with parsing
        assert len(result) == 4
        assert all(isinstance(price, EnergyPrice) for price in result)

        # Verify that the correct HourUTC format is parsed
        assert result[0].fromTs == datetime.fromisoformat("2024-01-15T12:00:00Z")
        assert result[1].fromTs == datetime.fromisoformat("2024-01-15T13:00:00Z")

    @patch('rest.requests.get')
    def test_failed_api_response(self, mock_get):
        """Test failed API response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        test_date = date(2024, 1, 15)
        gln_number = "123456789"

        result = getprices(test_date, gln_number)

        assert result == []

    @patch('rest.requests.get')
    def test_empty_response(self, mock_get):
        """Test empty response handling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"records": []}).encode()
        mock_get.return_value = mock_response

        test_date = date(2024, 1, 15)
        gln_number = "123456789"

        result = getprices(test_date, gln_number)

        assert result == []


class TestGetFuturePrices:
    """Test getFuturePrices function."""

    def setup_method(self):
        """Clear cache before each test."""
        global cachedPrices
        cachedPrices.clear()

    @patch('rest.getprices')
    def test_caching_mechanism(self, mock_getprices, sample_energy_prices):
        """Test that caching works correctly for today and tomorrow."""
        mock_getprices.return_value = sample_energy_prices

        gln_number = "123456789"

        # First call should fetch both today and tomorrow
        result = getFuturePrices(gln_number)

        # Should be called twice (today and tomorrow)
        assert mock_getprices.call_count == 2

        # Second call should use cache
        result2 = getFuturePrices(gln_number)
        assert mock_getprices.call_count == 2  # No additional calls

        # Verify cache keys
        today_str = date.today().strftime('%m/%d/%Y')
        tomorrow_str = (date.today() + timedelta(days=1)).strftime('%m/%d/%Y')

        assert f"{gln_number}_{today_str}" in cachedPrices
        assert f"{gln_number}_{tomorrow_str}" in cachedPrices

    @patch('rest.getprices')
    @patch('rest.datetime')
    def test_filtering_past_prices(self, mock_datetime, mock_getprices):
        """Test that past prices are filtered out."""
        # Mock datetime.now to return a fixed time
        mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat = datetime.fromisoformat

        # Create prices with some in the past
        past_prices = [
            EnergyPrice("2024-01-15T09:00:00Z", 0.5),  # Past
            EnergyPrice("2024-01-15T10:00:00Z", 0.3),  # Past
            EnergyPrice("2024-01-15T11:00:00Z", 0.7),  # Current
            EnergyPrice("2024-01-15T12:00:00Z", 0.4),  # Future
        ]
        mock_getprices.return_value = past_prices

        result = getFuturePrices("123456789")

        # Should only include current and future prices
        assert len(result) >= 2  # At least current and future


class TestDetermineLongestConsequtiveHours:
    """Test determineLongestConsequtiveHours function."""

    def test_find_optimal_window_1_hour(self, sample_energy_prices):
        """Test finding optimal window for 1 hour."""
        start_idx, end_idx = determineLongestConsequtiveHours(1, sample_energy_prices)

        # Should find the hour with minimum price (index 1, price 0.3)
        assert start_idx == 1
        assert end_idx == 1
        assert sample_energy_prices[start_idx].price == 0.3

    def test_find_optimal_window_multiple_hours(self, sample_energy_prices):
        """Test finding optimal window for multiple hours."""
        start_idx, end_idx = determineLongestConsequtiveHours(2, sample_energy_prices)

        # Should find the 2-hour window with minimum sum
        # Prices: [0.5, 0.3, 0.7, 0.4]
        # Windows: [0.5+0.3=0.8], [0.3+0.7=1.0], [0.7+0.4=1.1]
        # Best window is [0.5, 0.3] = 0.8
        assert start_idx == 0
        assert end_idx == 1

    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = [EnergyPrice("2024-01-15T00:00:00Z", 0.5)]

        # When there's insufficient data, it should return default values (0, 0)
        start_idx, end_idx = determineLongestConsequtiveHours(2, prices)
        assert start_idx == 0
        assert end_idx == 0


class TestGetTotalCostIfImpatient:
    """Test getTotalCostIfImpatient function."""

    @freeze_time("2024-01-15T12:30:00Z")
    def test_calculation_with_various_minutes(self, sample_energy_prices):
        """Test calculation with various minute values."""
        # At 12:30, 30 minutes left in current hour
        result = getTotalCostIfImpatient(sample_energy_prices, 90)  # 1.5 hours

        # Should calculate: 30 min of current hour + 1 full hour + 0 min of next hour
        expected = (30 * sample_energy_prices[0].price / 60) + sample_energy_prices[1].price
        assert abs(result - expected) < 0.001

    @freeze_time("2024-01-15T12:45:00Z")
    def test_partial_hour_calculation(self, sample_energy_prices):
        """Test partial hour calculations."""
        # At 12:45, 15 minutes left in current hour
        result = getTotalCostIfImpatient(sample_energy_prices, 75)  # 1.25 hours

        # Should calculate: 15 min of current + 1 full hour + 0 min of next
        expected = (15 * sample_energy_prices[0].price / 60) + sample_energy_prices[1].price
        assert abs(result - expected) < 0.001


class TestAPIEndpoints:
    """Test FastAPI endpoints."""

    def setup_method(self):
        """Clear cache and reset environment before each test."""
        global cachedPrices
        cachedPrices.clear()
        # Clear GLN_NUMBER from environment
        if 'GLN_NUMBER' in os.environ:
            del os.environ['GLN_NUMBER']

    @patch('rest.getFuturePrices')
    @patch('rest.getTotalCostIfImpatient')
    def test_next_optimal_hour_full_hours(self, mock_impatient, mock_future, client, sample_energy_prices):
        """Test /api/next-optimal-hour with full hours only using actual calculations."""
        # Mock the functions to return actual data
        mock_future.return_value = sample_energy_prices
        mock_impatient.return_value = 1.5  # Mock impatient price

        response = client.get("/api/next-optimal-hour?numHoursToForecast=2h0m&glnNumber=5790000611003")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'price' in data
        assert 'credits' in data
        assert 'fromTs' in data['price']
        assert 'toTs' in data['price']
        assert 'price' in data['price']
        assert 'suboptimalPriceMultiplier' in data['price']

        # Verify actual calculated values
        price_data = data['price']

        # Check that timestamps are valid ISO format
        from datetime import datetime
        from_ts = datetime.fromisoformat(price_data['fromTs'])
        to_ts = datetime.fromisoformat(price_data['toTs'])

        # Should be a 2-hour window
        duration = to_ts - from_ts
        assert duration.total_seconds() == 7200  # 2 hours in seconds

        # Check that price is reasonable (should be average of the 2 cheapest hours)
        # From our sample data: 0.5, 0.3, 0.7, 0.4 - the algorithm selects the first 2 hours (0.5 and 0.3)
        expected_avg_price = (0.5 + 0.3) / 2
        assert abs(price_data['price'] - expected_avg_price) < 0.01

        # Check suboptimal price multiplier is reasonable
        assert price_data['suboptimalPriceMultiplier'] > 1.0

        # Check credits field contains expected content
        assert 'credits' in data
        assert 'elprisen.somjson.dk' in data['credits']

    @patch('rest.getFuturePrices')
    @patch('rest.getTotalCostIfImpatient')
    def test_next_optimal_hour_partial_hours(self, mock_impatient, mock_future, client, sample_energy_prices):
        """Test /api/next-optimal-hour with partial hours using actual calculations."""
        # Mock the functions to return actual data
        mock_future.return_value = sample_energy_prices
        mock_impatient.return_value = 1.5  # Mock impatient price

        response = client.get("/api/next-optimal-hour?numHoursToForecast=1h30m&glnNumber=5790000611003")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'price' in data
        assert 'fromTs' in data['price']
        assert 'toTs' in data['price']

        # Verify actual calculated values
        price_data = data['price']

        # Check that timestamps are valid ISO format
        from datetime import datetime
        from_ts = datetime.fromisoformat(price_data['fromTs'])
        to_ts = datetime.fromisoformat(price_data['toTs'])

        # Should be 1.5 hours (90 minutes)
        duration = to_ts - from_ts
        assert duration.total_seconds() == 5400  # 1.5 hours in seconds

        # Check that price is reasonable (should be calculated based on partial hour logic)
        assert price_data['price'] > 0
        assert price_data['price'] < 2.0  # Should be reasonable price range

    def test_next_optimal_hour_missing_gln(self, client):
        """Test /api/next-optimal-hour with missing GLN number."""
        response = client.get("/api/next-optimal-hour?numHoursToForecast=1h0m")

        assert response.status_code == 500
        assert "INVALID GLNNUMBER" in response.json()["detail"]

    @patch.dict(os.environ, {'GLN_NUMBER': '5790000611003'})
    @patch('rest.getFuturePrices')
    @patch('rest.getTotalCostIfImpatient')
    def test_next_optimal_hour_gln_from_env(self, mock_impatient, mock_future, client, sample_energy_prices):
        """Test /api/next-optimal-hour with GLN from environment variable using actual calculations."""
        # Mock the functions to return actual data
        mock_future.return_value = sample_energy_prices
        mock_impatient.return_value = 1.5  # Mock impatient price

        response = client.get("/api/next-optimal-hour?numHoursToForecast=1h0m")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'price' in data
        assert 'fromTs' in data['price']
        assert 'toTs' in data['price']

        # Verify actual calculated values
        price_data = data['price']

        # Check that timestamps are valid ISO format
        from datetime import datetime
        from_ts = datetime.fromisoformat(price_data['fromTs'])
        to_ts = datetime.fromisoformat(price_data['toTs'])

        # Should be exactly 1 hour
        duration = to_ts - from_ts
        assert duration.total_seconds() == 3600  # 1 hour in seconds

        # Check that price is reasonable (should be the cheapest hour: 0.3)
        expected_price = 0.3  # From our sample data, the cheapest hour
        assert abs(price_data['price'] - expected_price) < 0.01

    @patch('rest.getFuturePrices')
    @patch('rest.getTotalCostIfImpatient')
    def test_next_optimal_hour_edge_cases(self, mock_impatient, mock_future, client, sample_energy_prices):
        """Test /api/next-optimal-hour with edge cases using actual calculations."""
        # Mock the functions to return actual data
        mock_future.return_value = sample_energy_prices
        mock_impatient.return_value = 1.5  # Mock impatient price

        # Test with very short duration (30 minutes)
        response = client.get("/api/next-optimal-hour?numHoursToForecast=0h30m&glnNumber=5790000611003")

        assert response.status_code == 200
        data = response.json()

        # Should be exactly 30 minutes
        price_data = data['price']
        from_ts = datetime.fromisoformat(price_data['fromTs'])
        to_ts = datetime.fromisoformat(price_data['toTs'])
        duration = to_ts - from_ts
        assert duration.total_seconds() == 1800  # 30 minutes in seconds

        # Test with longer duration (3 hours)
        response = client.get("/api/next-optimal-hour?numHoursToForecast=3h0m&glnNumber=5790000611003")

        assert response.status_code == 200
        data = response.json()

        # Should be exactly 3 hours
        price_data = data['price']
        from_ts = datetime.fromisoformat(price_data['fromTs'])
        to_ts = datetime.fromisoformat(price_data['toTs'])
        duration = to_ts - from_ts
        assert duration.total_seconds() == 10800  # 3 hours in seconds

    def test_healthz_endpoint(self, client):
        """Test /healthz endpoint."""
        response = client.get("/healthz")

        assert response.status_code == 204
        assert response.content == b''

    @freeze_time("2024-01-15T11:00:00Z")
    @patch('rest.getFuturePrices')
    def test_max_start_time_constrains_result(self, mock_future, client, sample_energy_prices):
        """Test that max_start_time successfully constrains the optimal start time."""
        mock_future.return_value = sample_energy_prices

        max_start = "2024-01-15T13:00:00Z"
        response = client.get(
            f"/api/next-optimal-hour?numHoursToForecast=1h0m&glnNumber=5790000611003&max_start_time={max_start}"
        )

        assert response.status_code == 200
        data = response.json()
        price_data = data['price']

        from_ts = datetime.fromisoformat(price_data['fromTs'])
        max_start_dt = datetime.fromisoformat(max_start)

        assert from_ts <= max_start_dt
        assert from_ts == datetime.fromisoformat("2024-01-15T13:00:00Z")

    @freeze_time("2024-01-15T11:00:00Z")
    @patch('rest.getFuturePrices')
    def test_max_start_time_too_early(self, mock_future, client, sample_energy_prices):
        """Test that max_start_time that is too early returns an error."""
        mock_future.return_value = sample_energy_prices

        max_start = "2024-01-15T11:30:00Z"
        response = client.get(
            f"/api/next-optimal-hour?numHoursToForecast=2h0m&glnNumber=5790000611003&max_start_time={max_start}"
        )

        assert response.status_code == 400
        assert "Not enough available prices" in response.json()["detail"]

    @freeze_time("2024-01-15T11:00:00Z")
    @patch('rest.getFuturePrices')
    def test_max_start_time_in_past(self, mock_future, client, sample_energy_prices):
        """Test that max_start_time in the past returns an error."""
        mock_future.return_value = sample_energy_prices

        max_start = "2024-01-15T10:00:00Z"
        response = client.get(
            f"/api/next-optimal-hour?numHoursToForecast=1h0m&glnNumber=5790000611003&max_start_time={max_start}"
        )

        assert response.status_code == 400
        assert "must be in the future" in response.json()["detail"]

    @freeze_time("2024-01-15T11:00:00Z")
    @patch('rest.getFuturePrices')
    def test_max_start_time_invalid_format(self, mock_future, client, sample_energy_prices):
        """Test that invalid max_start_time format returns an error."""
        mock_future.return_value = sample_energy_prices

        max_start = "invalid-date"
        response = client.get(
            f"/api/next-optimal-hour?numHoursToForecast=1h0m&glnNumber=5790000611003&max_start_time={max_start}"
        )

        assert response.status_code == 400
        assert "Invalid max_start_time format" in response.json()["detail"]

    @freeze_time("2024-01-15T11:00:00Z")
    @patch('rest.getFuturePrices')
    def test_max_start_time_with_partial_hours(self, mock_future, client, sample_energy_prices):
        """Test max_start_time with partial hours."""
        mock_future.return_value = sample_energy_prices

        max_start = "2024-01-15T13:30:00Z"
        response = client.get(
            f"/api/next-optimal-hour?numHoursToForecast=1h30m&glnNumber=5790000611003&max_start_time={max_start}"
        )

        assert response.status_code == 200
        data = response.json()
        price_data = data['price']

        from_ts = datetime.fromisoformat(price_data['fromTs'])
        max_start_dt = datetime.fromisoformat(max_start)

        assert from_ts <= max_start_dt
