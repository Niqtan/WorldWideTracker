from unittest import mock
import pytest
import sys
import os

# Add the 'src' directory (inside 'WorldWideTracker') to sys.path
src_path = os.path.abspath(r'C:\Users\SHARKY\Documents\Python Files\CS50P_Lecture_Files\Final\WorldWideTracker\src')
sys.path.append(src_path)
from project import set_goals, recommend_goals, load_main_config
#Classes to import
from project import Log
#Integration Testing
import psycopg2
from config import config


@pytest.fixture
def test_log_init():
    return Log("Strudel, apple", 274, "100g")

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
    crsr.execute(
        query, ('Strudel, apple', '100g', '274', '12:12:12')) 
    
    connection.commit()

    yield connection

    crsr.execute("DELETE FROM test_table")
    connection.commit()
    connection.close()

def test_viewmeals_with_database(test_database_integration):

    crsr = test_database_integration.cursor()
    crsr.execute("""
                SELECT *  FROM test_table
        """)
    result = crsr.fetchall()
    for row in result: 
        assert "Strudel, apple" in row

#Unit Tests
def test_logging_default(test_log_init):
    with mock.patch('builtins.input') as mock_input:
        mock_input.side_effect = ['Y']
    
    assert test_log_init.log() == "Logged Successfully"

def test_manual_logging(test_log_init):
    with mock.patch('builtins.input') as mock_input:
        mock_input.side_effect = [ 'banana', '104', '1 medium']
    

        assert test_log_init.manual() == "Logged Successfully"


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


