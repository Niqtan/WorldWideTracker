from unittest import mock
import pytest

#Functions to import
from src.project import set_goals, recommend_goals, load_main_config, load_branded_config, food_log, load_database_1_days, view_meals, barcode_scanner
#Classes to import
from src.project import Log, Menu, Meal
#Integration Testing
import psycopg2
from src.config import config


@pytest.fixture
def test_log_init():
    return Log("Strudel, apple", 274, "100g")

#Integration Tests (Databases (Foundation), Viewmeals Function (), questionary Mock)
@pytest.fixture
def test_database_integration():
    connection = None
    params = config()
    connection = psycopg2.connect(**params)

    crsr = connection.cursor()

    crsr.execute("DELETE FROM test_table")
    crsr.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
        meal_logged varchar(100),
        serving varchar(25),
        calorie numeric(6, 2),
        date_meal time);  
    """)

    query = "INSERT INTO test_table VALUES (%s, %s, %s, %s)"
    #Using the real database (not mocking anything), we are doing this
    #to see if our REAL database can handle the values and return as expected
    crsr.execute(
        query, ('Strudel, apple', '100g', '274', '12:12:12')) 
    
    connection.commit()

    yield connection

    crsr.execute("DELETE FROM test_table")
    connection.commit()
    connection.close()

def test_viewmeals_with_database(test_database_integration): #Don't pass in mock as a parameter since

    crsr = test_database_integration.cursor()
    crsr.execute("""
                SELECT *  FROM test_table
        """)
    result = crsr.fetchall()
    #How shall I use my view_meals function here?
    for row in result: #Index into result and get the row of the meal name
        assert "Strudel, apple" in row

#Unit Tests
def test_logging_default(test_log_init):
    with mock.patch('builtins.input') as mock_input:
        mock_input.return_value = "Y"
    
    assert test_log_init.log() == "Logged Successfully!"


@mock.patch("questionary.select")
@mock.patch("psycopg2.connect")
def test_database_view_meals(mock_select, mock_connect):
    mock_select.return_value.ask.return_value = "1. Today's Meals"
    mock_cursor = mock_connect.return_value.cursor.return_value
    #Test the database with view_meals
    #Assert that view meals will have this amount of calories left
    assert mock_cursor.called
    

@mock.patch("psycopg2.connect")
def test_database_goals(mock_connect):
    mock_cursor = mock_connect.return_value.cursor.return_value #Mock the connection
    mock_cursor.execute = mock.Mock()
    mock_connect #Continue with mocking the connection and mock the goals
    #Perhaps check if the connection is commiting for goal calories? How do I do that?
    

#Mock testing functions
@mock.patch("builtins.input", side_effect=[53.2, 60.0, 2.0, "y"]) #Replaces the specific object with a mock object
#Side effect attribute allows you to specify what happens when a mock is called
def test_goals(mock_input):
    goals = set_goals()
    assert goals == {"current_weight": 53.2,
                     "target_weight": 60,
                     "activity_level": 2}
    goals_recommend = recommend_goals()
    assert goals_recommend == 3525

'''
Some Reminders:
1) Use pytest first again to see whats going wrong
2) Perhaps the problem is that the assertion error is bad but the mock
function itself isn't, so only change how the mock function is being asserted.
'''

mock_response = {
    "totalHits": 1,
    "foods": [ #Index 0
        {
            "fdcId": 170379,
            "dataType": "Branded",
            "description": "BROCCOLI",
            "foodCode": "string",
            "foodNutrients": [
                {
                    "nutrientId": 1003,
                    "nutrientName": "Energy",
                    "unitName": "kcal",
                    "value": 55
                }
            ]
        }
    ]
}

@mock.patch('requests.get')
def test_API(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response

    food = load_main_config("broccoli")
    assert food['foods'][0]['description'] == "BROCCOLI"

    #Try testing the food_log function
@mock.patch("questionary.text", return_value=["apple"])
def test_log(mock_input):
    log = food_log()
    result = log("apple")
    assert result == "1. Croissants"

