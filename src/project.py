#Functionality
import requests, psycopg2, random, os
from datetime import datetime
from config import config
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from dotenv import load_dotenv

#Quality of Life:
from rich import print as rprint
import questionary
from tabulate import tabulate

load_dotenv()
API_KEY = os.getenv('API_KEY')

#Global Variables here:
class Log:
    def __init__(self, food=None, calories=0, serving_size='100g',
                date=datetime.today().strftime('%Y-%m-%d'),
                time=datetime.today().strftime('%H:%M:%S'),
                date_and_time=datetime.today().strftime('%Y-%m-%d %H:%M:%S')):
        self.food_name = food
        self.calories = calories
        self.serving_size = serving_size
        self.date = date
        self.time = time
        self.date_and_time = date_and_time

    def log(self):
        #How to log this?
        if self.food_name and self.calories and self.serving_size:
            food_entries.append({
            "food": self.food_name,
            "calories": self.calories,
            "serving_size": self.serving_size,
            "time": self.time,
            "date_and_time": self.date_and_time
            })
            print("Logged Successfully!") #Calling the function itself will create another database
            post_prompt = Menu("Would you like to return back to the main menu? (Y/N): ")
            post_prompt.post_prompt()
            return "Logged Successfully!"

    @classmethod
    def manual(self):
        while True:
            try:
                food_name = input("Enter Food name: ")
                calories = int(input("Enter calories: "))
                serving_size = input("Enter the serving size: ")
                if food_name and calories and serving_size:
                    food_entries.append({
                    "food": food_name,
                    "calories": calories,
                    "serving_size": serving_size,
                    'time': self.time,
                    "date_and_time": self.date_and_time,
                    })
                    print("Logged Successfully!\n")
                    post_prompt = Menu("Would you like to return back to the main menu? (Y/N) ")
                    post_prompt.post_prompt()
            except ValueError:
                print("Please enter a valid prompt.")
                pass

class Meal:
    def __init__(self):
        self.meal_data = None

    def get_meal(self, crsr):
        crsr.execute("SELECT calorie from food_data")
        #passing in crsr as a parameter is needed here because
        #Load databases primarily defines this, and passing in crsr here
        #Makes it so that you are able to execute SQL commands
        self.meal_data = crsr.fetchall()
        #self.meal_data simply acts as an instance variable and just
        #used for recycling
        calorie_list = [row[0] for row in self.meal_data]
        #Basically says, "Get every row from every calorie row in food_data"
        return calorie_list

class Menu:
    def __init__(self, prompt):
        self.prompt = prompt

    def post_prompt(self):
        while True:
            prompt = input(self.prompt)
            if prompt == "y":
                put_database()
                main()
            elif prompt == "n":
                put_database()
                food_log()

"""
If we make time also have date, then that means that changing
the table on the database would be necessary --> Option 1
Option 2: Try to find a way to refactor out the code
in the database function --> Optimal
Option 3: Create a new function with a new database containing
all 30 days. However, that would now be separate from the
new database --> Ton of work


Perhaps what we could do is to do option 2
"""
food_entries = []

#Basic Menu here
def main():
    rprint("\n WELCOME TO THE WorldWideTracker! \n")
    rprint("===Making calorie tracking easy===\n")

    questions = questionary.select(
        "What do you want to do?",
        choices=["1. Log your food", "2. View your Log", "3. Set your goals (Receive Reminders as well)", "4. Scan a barcode (For Branded Foods)", "5. Exit"],
    ).ask()


    while True:
        match questions:
            case "1. Log your food":
                food_log()
            case "2. View your Log":
                view_meals()
            case "3. Set your goals (Receive Reminders as well)":
                set_goals()
                recommend_goals()
                while True:
                    #Debug this if this will work...
                    prompt = input("Would you like to return back to the main menu? (Y/N) ").lower()
                    if prompt == "y":
                        main()
                    elif prompt == "n":
                        set_goals()
                        recommend_goals()
                    else:
                        pass
            case "4. Scan a barcode (For Branded Foods)":
                barcode_scanner()
            case "5. Exit":
                exit("Thank you for using the WorldWideTracker!")

url = "https://api.nal.usda.gov/fdc/v1/foods/search"

#USDA API database here
def load_config(name, data_type):
    response = requests.get(
        url, params={"query": f"{name}", "dataType": data_type, "pageSize": 3,  "api_key": API_KEY })
    #Use Parameters in order to filter out results

    #Use .json to open get the data
    try:
        if response.status_code == 200: #Response code 200 to know its True
            food_data = response.json() #Convert to JSON file which consists of key value pairs
            if food_data and food_data.get("totalHits"):
                print("Looking for this?")
                return food_data
        else:
            raise ValueError

    except(ValueError):
        print("Invalid. Please try again")
        pass

def load_main_config(name):
    return load_config(name, ["Foundation", "SR Legacy"])

def load_branded_config(name):
    return load_config(name, ["Branded"])

def load_database(delete_query, select_query):
    #Connects the config file (SQL) to the python file
    try:
        connection = None
        params = config()
        connection = psycopg2.connect(**params)


        #The cursor allows you to use commands and retrieve results
        #Checks if the cursor is connecting

        crsr = connection.cursor()

        #Food Data
        crsr.execute("""
            CREATE TABLE IF NOT EXISTS food_data (
                meal_logged varchar(100),
                serving varchar(25),
                calorie numeric(6, 2),
                date_meal time);
            """)        
        crsr.execute("""
            CREATE TABLE IF NOT EXISTS food_data_30_days (
            meal_logged varchar(100),
            serving varchar(25),
            calorie numeric(6, 2));             
        """)

        crsr.execute(select_query)
        food_data_result = crsr.fetchall()
        header = ["Food Name", "Serving Size", "KCAL", "Time of Log"]
        
        crsr.execute(
            delete_query
        )
        
        crsr.execute("""
                CREATE TABLE IF NOT EXISTS calorie_goals3(
                    recommended_calories numeric(6,2)
                );
        """)
        
        connection.commit()

        page_counter = 1
        rows_per_page = 6
        
        #Mostly used variables should be outside to avoid resetting values
        #And updates instead of RESETTING back to their original values
        while True:
            start_page = (page_counter - 1) * rows_per_page 
            end_page = start_page + rows_per_page 

            limit_food_data_result = food_data_result[start_page:end_page]
            
            if page_counter > 0 and len(food_data_result) + 6 > end_page:
                print(tabulate(limit_food_data_result, headers=header, tablefmt="grid"))
            else:
                print("No more pages to show.")

            page_questionare = questionary.select(
                " == Logged Meals == ",
                choices = ["1. Next Page", "2. Back Page", "3. Back to view"]
                ).ask()
            match page_questionare:
                case "1. Next Page":
                    page_counter += 1
                case "2. Back Page":
                    if page_counter > 0:
                        page_counter -= 1
                case "3. Back to view":
                    view_meals()

        
        #Logic for flipping through the pages
            
        #Calorie Goals
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        #Allows for cleanup tasks and shows that database connection is closed
        #if something went wrong with the connection
        if connection is not None:
            crsr.close()
            connection.close()
        #if connection is not None (Since connection is now
        # defined via the unpacking of pspcopg2.connect), close the connection

def load_database_1_days():
    return load_database("DELETE FROM food_data WHERE date_meal > (NOW() + INTERVAL '24 HOURS')::time",
                         "SELECT meal_logged, serving, calorie, date_meal FROM food_data ORDER BY date_meal DESC;")
    #Basically says: if the meal logged at a certain time is earlier than the time
    #now minus 24 hours, then it will delete the food_data table

    #The deleting of the 30 days function will not work since both the 1
    # days and 30 days delete the food data anyways

def load_database_30_days():
    return load_database("DELETE FROM food_data_30_days WHERE date_and_time::time > (NOW() + INTERVAL '720 HOURS')::time",
                         """SELECT meal_logged, serving, calorie,
                          CONCAT(LPAD(month::varchar(15), 2, '0'), '-', LPAD(day::varchar(15), 2, '0'), ' ', LPAD(hour::varchar(15), 2 ,'0'), ':', LPAD(minute::varchar(15), 2, '0'), ':', LPAD(second::varchar(15), 2, '0')) AS date_and_time_logged
                          FROM food_data_30_days
                          ORDER BY date_and_time_logged DESC;
                          """)
def put_database():
    connection = None
    params = config()
    connection = psycopg2.connect(**params)

        #The cursor allows you to use commands and retrieve results
        #Checks if the cursor is connecting

    crsr = connection.cursor()
    table1 = "food_data"
    table2 = "food_data_30_days"

    if table1:
        full_query = f"INSERT INTO {table1} VALUES (%s, %s, %s, %s);"
        for entry in food_entries:
            crsr.execute(
                full_query, (entry['food'], entry['serving_size'], entry['calories'], entry['time'])
            )
        crsr.execute("SELECT * FROM food_data;")

    if table2:
        full_query2 = f"INSERT INTO {table2} VALUES (%s, %s, %s, %s, DEFAULT, DEFAULT, DEFAULT, DEFAULT, DEFAULT);"
        for entry in food_entries:
            crsr.execute(
                full_query2, (entry['food'], entry['serving_size'], entry['calories'], entry['date_and_time'])
            )
        crsr.execute("SELECT * FROM food_data_30_days;")
    
    connection.commit()
#Logging a meal wit the USDA
def food_log():
    global food, calorie
    food_results = []
    cal_results = []

    while True:
        search_food = questionary.text("Log a food (Be specific): ").ask()
        call_api = load_main_config(search_food)
        if call_api != None:
            for _ in range(1): #Iterate over each food item
                for i, result in enumerate(call_api['foods']):
                        food_results.append(result['description'])
                        for energy in result['foodNutrients']:
                            if energy['unitName'] == 'KCAL':
                                divided_energy = int(energy['value'])
                                cal_results.append(divided_energy)
                                rprint(f"{i+1}. {result['description']} ({divided_energy} kcal per 100g)")

                                    #How to return for pytest
            print("4. Can't find what you're looking for? Enter it manually.")
            print("5. Log a new one")
            break
        else:
            print("Does not exist within the database. Sorry!")
            continue

    while True:
        if call_api != None:
            user_input = input("Please enter a number between 1-5: ")
            if user_input in {"1", "2", "3"}:
                index = int(user_input) - 1
                food = food_results[index]
                calorie = cal_results[index]
                serving_size = "100g"
                log_instance = Log(food, calorie, serving_size)
                food_options = {
                    "1": log_instance.log, #OOP function here to log the food
                    "2": log_instance.log,
                    "3": log_instance.log,
                }
                food_options[user_input]()
            elif user_input in {"4", "5"}:
                food = None
                calorie = None
                food_options = {
                    "4": Log.manual,
                    "5": food_log
                }
                food_options[user_input]()
            else:
                print("Please choose a valid number.")

def view_meals():
    meal = Meal()
    log = Log()
    #Bug: This function is also not working because past calories of a food is # not logged or rather not accounted for when I open a fresh program
    questionare = questionary.select(
        " == Logged Meals == ",
        choices = ["1. Today's Meals", "2. Meals in the Last 30 Days", "3. Back to Main Menu" ],
    ).ask()

    """
    Initiates the database to be used for loading the data as a
    visual representation to the user. This is the 2nd part of
    loading the database for the saving the goal_calories
    """

    params = config()
    connection = psycopg2.connect(**params)
    crsr = connection.cursor()

    crsr.execute("SELECT recommended_calories FROM calorie_goals3;")
    result_crsr = crsr.fetchone()

    if result_crsr is None: #If no goal calories is found, then prompt if they want to set goals first
        while True:
            prompt = input("Would you like to set your goals for reminders of your calorie intake? (Y/N): ").lower()
            if prompt == "y":
                set_goals()
                recommend_goals()
            elif prompt == "n":
                view_meals()
            else:
                pass
    else:
        goal_calories = result_crsr[0] #Look through the values of fetchone and assign that value to goal_calories

    match questionare:
        case "1. Today's Meals":
            print(f"Logged Meals as of {log.date}:")
            if goal_calories:
                total_calories = int(sum(meal.get_meal(crsr)))
                final_calories = int(goal_calories) - total_calories
                if final_calories:
                    if goal_calories > final_calories:
                        print(f"\nRemaining Calories for the day: {int(final_calories)}")
                        print("You're well under your calorie goal... Good job!")
                    elif goal_calories < final_calories:
                        print(f"You're over {int(final_calories)} calories of your original calorie goal\n")
            load_database_1_days()
        case "2. Meals in the Last 30 Days":
                print(f"\nLogged Meals over the past 30 days:")
                load_database_30_days()
        case "3. Back to Main Menu":
            main()

    #Add a function for todays meals to display how many calories under
    #or over the actual goal of calories

goals = {
    "current_weight": None,
    "target_weight": None,
    "activity_level": None
}
#Setting/Updating Goals
def set_goals():
    questions = ["Current Weight (kg): ", "Target Weight (kg): ", "Activity Level: "]
    responses = []

    for question in questions:
        if question == "Activity Level: ":
            print("\nSelect your activity level: ")
            print("1. Sedentary (little to no exercise)")
            print("2. Lightly Active (light physical activity 1-2 days a week)")
            print("3. Moderately Active (Regular physical activity 3-5 days a week)")
            print("4. Very Active (Hard physical activity 6-7 days a week)\n")
        while True:
            try:
                response = float(input(question))
                responses.append(response)
                break
            except ValueError:
                print("Please give a valid number")
                pass

    goals["current_weight"] = responses[0]
    goals["target_weight"] = responses[1]
    goals["activity_level"] = responses[2]

    return goals

def recommend_goals():
    goal_calories = 0
    calorie_multiplier = 1
    if goals["activity_level"] == 1:
        calorie_multiplier = 1.2
    elif goals["activity_level"] == 2:
        calorie_multiplier = 1.375
    elif goals["activity_level"] == 3:
        calorie_multiplier = 1.55
    elif goals["activity_level"] == 4:
        calorie_multiplier = 1.725
    else:
        print("Invalid activity level given")
        print("Setting Calorie Multiplier to 1...")
        calorie_multiplier = 1

    calories = 2200 * calorie_multiplier

    if goals["current_weight"] > goals["target_weight"]:
        goal_calories = calories - 500
    elif goals["current_weight"] < goals["target_weight"]:
        goal_calories = calories + 500
    print(f"Your recommended calorie intake is {int(goal_calories)} kcal per day")

    while True:
        reminder_prompt = input("Would you like to receive reminders of your calorie goals? (Y/N): ").lower()
        if reminder_prompt == "y":
            print("Great! We’ll send you a reminder when you’re on our View Meals tab.")
            goal_calories = int(goal_calories)
            break
        elif reminder_prompt == "n":
            print("No problem! Let us know if you change your mind.")
            goal_calories = None
            #If picked "n", it doesnt follow the reminder
            #Meaning that if I picked n, it will still display the calories.
            break
        else:
            print("Invalid Input. Please enter Y or N")

    """
    In order to solve my problem of which the goals wasn't saving on a
    fresh program start, I've divided the database into two parts:
    One for saving the data for the variable goal_calories, and one
    for loading that data which is defined in the view_meals
    """
    params = config()
    #Config file makes your code more clean
    connection = psycopg2.connect(**params)
    crsr = connection.cursor()
    if goal_calories is not None:
        query = """
        UPDATE calorie_goals3
        SET recommended_calories = (%s);
        """
        crsr.execute(query, (goal_calories,))
        #Updates the table for none first-timers and sets the row a new value
        #depending on goal_calories
        connection.commit()

    crsr.close()
    connection.close()

    return goal_calories

def barcode_scanner():
    while True:
        prompt = input("Allow Access to your Camera? (Y/N): ").lower()
        if prompt == "y":
            cap = cv2.VideoCapture(0)

            while True:
                ret, frame = cap.read()
                
                barcode_scan = decode(frame)

                if not barcode_scan:
                    print("No barcode detected")

                for qr_code in barcode_scan:
                    
                    #cv2.rectangle(image, (start_point as tuple), (end_point as tuple), color, thickness)
                    barcodeData = qr_code.data
                    barcodeType = qr_code.type

                    print(f"Found type: {barcodeType} Barcode: {barcodeData}")

                    """
                    What to do:
                    1. Use the pyzbar in order to detect QR codes
                    2. Get the data from these qr codes and search it in the API
                    3. Using the API, if detected, then say "Logged successfully", if not then prompt the user again
                    4. Make sure this barcode function has great error detecting skillz
                    """
                    #Continue on with this
                    ''' Known methods for implementation:
                    1. Calculate the rectangular position of the barcode (x,y) as a tuple
                    2. The problem still persists: How do I get the data from the barcode? (Data is already in the qr code)
                    3. Either use cv2.rectangle method
                    '''
                    #We want to first identify the barcode and its rectangular position
                    #Then, we go and get the data from that and print it
                    #Log it as well
                    #load_branded_config
                    #print("Detected! Found {}")

                cv2.imshow('QR Code Scanner', frame)
                if not ret:
                    print("Could not open webcam.")
                    continue

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            cap.release()
            cv2.destroyAllWindows()
            main()
        elif prompt == "n":
            main()
        else:
            print("PLEASEE")
            pass


if __name__ == "__main__":
    main()

