from flask import Flask, render_template, request, url_for, redirect, session
import pymongo
import bcrypt
import pandas as pd
import requests  
from bs4 import BeautifulSoup
import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import requests
import pymongo
import os

# This is for when deploying to Heroku
# chrome_options = webdriver.ChromeOptions()
# chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--no-sandbox")
# driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

#set app as a Flask instance 
app = Flask(__name__)

# This is for when deploying to Heroku
# app.config.update(
#     GOOGLE_CHROME_BIN = 
#     CHROMEDRIVER_PATH = "/"
# )

#encryption relies on secret keys so they could be run
app.secret_key = "testing"
#connect to your Mongo DB database
client = pymongo.MongoClient("mongodb+srv://sebastiandifrancesco:badass88@cluster0.gnjhr.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

#get the database name
db = client.mtg_drafts
#get the particular collection that contains the data
records = db.user_records

def getdata(url):  
    r = requests.get(url)  
    return r.text

#assign URLs to have a particular route
# Index page/Registration page 
@app.route("/", methods=['post', 'get'])
def index():
    message = ''
    #if method post in index
    if "email" in session:
        return redirect(url_for("logged_in"))
    if request.method == "POST":
        user = request.form.get("fullname")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        #if found in database showcase that it's found 
        user_found = records.find_one({"name": user})
        email_found = records.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that name'
            return render_template('index.html', message=message)
        if email_found:
            message = 'This email already exists in database'
            return render_template('index.html', message=message)
        if password1 != password2:
            message = 'Passwords should match!'
            return render_template('index.html', message=message)
        else:
            #hash the password and encode it
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            #assing them in a dictionary in key value pairs
            user_input = {'name': user, 'email': email, 'password': hashed, 'Cubes':[], 'Drafts':[]}
            #insert it in the record collection
            records.insert_one(user_input)
            
            #find the new created account and its email
            user_data = records.find_one({"email": email})
            new_email = user_data['email']
            #if registered redirect to logged in as the registered user
            return render_template('logged_in.html', email=new_email)
    return render_template('index.html')


# Login page
@app.route("/login", methods=["POST", "GET"])
def login():
    message = 'Please login to your account'
    if "email" in session:
        return redirect(url_for("logged_in"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        #check if email exists in database
        email_found = records.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']
            #encode the password and check if it matches
            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["email"] = email_val
                return redirect(url_for('logged_in'))
            else:
                if "email" in session:
                    return redirect(url_for("logged_in"))
                message = 'Wrong password'
                return render_template('login.html', message=message)
        else:
            message = 'Email not found'
            return render_template('login.html', message=message)
    return render_template('login.html', message=message)

# This is the account page
@app.route('/logged_in')
def logged_in():
    if "email" in session:
        email = session["email"]
        return render_template('logged_in.html', email=email)
    else:
        return redirect(url_for("login"))

# Logout page
@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
        return render_template("signout.html")
    else:
        return render_template('index.html')

# For uploading an excel file cube or set to the database
# (columns must be called Name and Set and sets must be full set names with abbreviations in parantheses like they are on scryfall.com)
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and "email" in session:
        email = session["email"]
        cube_name = request.form.get("cubename")
        df = pd.read_csv(request.files.get('file'))
        # Tests for if file input was saved correctly to the df
        # return render_template('upload.html', data=cube_name)

        # Initialize PyMongo to work with MongoDBs
        conn = 'mongodb+srv://sebastiandifrancesco:badass88@cluster0.gnjhr.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
        client = pymongo.MongoClient(conn)

        # Define database and collection
        db = client.mtg_drafts
        myquery = {"email":email}
        collection = db.user_records.find(myquery)

        # Read in DF and create two new dataframed one holding the card names and one holding the which set each card belongs to
        df_name = df[["Name"]]
        df_set = df["Set"].tolist()

        # Fill mtg_cards with names and sets
        mtg_cards = {}
        for card in df_name["Name"]:
            mtg_cards[card] = []
        count = 0
        for card in mtg_cards:
            mtg_cards[card].append({'Set' : df_set[count]})
            count += 1

        # Web Scraping    
        for card in mtg_cards:
            try:
                # Navigates to the cards scryfall page using the Name and Set Name (must be identical to scryfall)
                driver = webdriver.Chrome()
                driver.get("https://scryfall.com/advanced")
                search_box = driver.find_element_by_name("name")
                search_box.send_keys(str(card))
                search_box = driver.find_element_by_name("name")
                set_box = driver.find_element_by_xpath("/html/body/div[3]/form/div/div[9]/div/div[1]/span/span[1]/span/ul/li/input")
                set_box.send_keys(str(mtg_cards[card][0]['Set']))
                set_box.send_keys(Keys.DOWN)
                set_box.send_keys(u'\ue007')
                search_button = driver.find_element_by_xpath("//button[@class='button-n submit-n']")
                search_button.click()
                url = driver.current_url
                htmldata = getdata(url)  
                soup = BeautifulSoup(htmldata, 'html.parser')
                
                # Retrieve card info
                results = soup.find_all('div', class_='card-profile')
                for result in results:
                    for item in soup.find_all('img'): 
                        image_url = item['src']
                    mtg_card_name = result.find('h1', class_='card-text-title').text.strip().split('\n')[0]
                    mtg_card_set = result.find('span', class_='prints-current-set-name').text.split('\n')[1].strip()
                    mtg_card = {'cube_name':cube_name,
                                'card_image_url':image_url,
                                'mtg_card_name':mtg_card_name,
                                'mtg_card_set':mtg_card_set,
                                "owner's_email":email}
                    
                    # Insert Card Data into mongoDB
                    db.user_records.update({ 'email': email }, { '$push': { 'Cubes' : mtg_card } })

                    # collection.insert_one(mtg_card)
                driver.quit()
            #     This will output clickable image url
            #     print(cards[card][1]['Image URL'])
            # If a card is not found print ERROR msg and save card name to list of mtg cards not found
            except:
                print("ERROR")
                print(card)
        # Convert entire collection to Pandas dataframe
        cube = pd.DataFrame(list(records.find(myquery)))
        cube_card_objects = cube.Cubes.all()
        cube_card_objects_df = pd.DataFrame(cube_card_objects)
        # Filter for only names and sets
        df_names_sets = df[['Name','Set']]
        cube_names = cube_card_objects_df[['mtg_card_name','mtg_card_set']]
        # Combine data
        merged_df = pd.merge(df_names_sets, cube_names, left_on='Name', right_on='mtg_card_name', how='outer')
        # Find the rows with null values to see missing cards
        null_data = merged_df[merged_df.isnull().any(axis=1)]
        test_set = null_data[['Name']].dropna()
        miss_indexes = test_set.index
        miss_mtg_card_names = test_set.Name
        miss_mtg_card_names_lst = miss_mtg_card_names.tolist()
        global miss_mtg_card_names_lst_glob 
        miss_mtg_card_names_lst_glob = miss_mtg_card_names_lst
        if len(miss_mtg_card_names_lst) > 0:
            return redirect('http://127.0.0.1:5000/manual_upload')

        else:
            return render_template('upload.html')
    return render_template('upload.html')

# For uploading an excel file cube or set to the database
@app.route('/manual_upload', methods=['GET', 'POST'])
def manual_upload():
    # if len(miss_mtg_card_names_lst_glob) != 0:
    #     print(miss_mtg_card_names_lst_glob)
    miss_mtg_card_names_lst = ''
    if request.method == 'POST' and "email" in session:
        email = session["email"]
        cube_name = request.form.get("cubename")
        url = request.form.get("cardlink")
        print(url)
        # Initialize PyMongo to work with MongoDBs
        conn = 'mongodb+srv://sebastiandifrancesco:badass88@cluster0.gnjhr.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
        client = pymongo.MongoClient(conn)

        # Define database and collection
        db = client.mtg_drafts
        myquery = {"email":email}
        collection = db.user_records.find(myquery)
        
        try:
            # Navigates to the cards scryfall page using the Name and Set Name (must be identical to scryfall)
            htmldata = getdata(url)  
            soup = BeautifulSoup(htmldata, 'html.parser')
            print(soup)    
            # Retrieve card info
            results = soup.find_all('div', class_='card-profile')
            for result in results:
                for item in soup.find_all('img'): 
                    image_url = item['src']
                mtg_card_name = result.find('h1', class_='card-text-title').text.strip().split('\n')[0]
                mtg_card_set = result.find('span', class_='prints-current-set-name').text.split('\n')[1].strip()
                mtg_card = {'cube_name':cube_name,
                            'card_image_url':image_url,
                            'mtg_card_name':mtg_card_name,
                            'mtg_card_set':mtg_card_set,
                            "owner's_email":email}
                db.user_records.update({ 'email': email }, { '$push': { 'Cubes' : mtg_card } })
                # test.insert_one(mtg_card)
        # If a card is not found print ERROR msg and save card name to list of mtg cards not found
        except:
            miss_mtg_card_names_lst = 'error'
            print("ERROR")
            # print(card)
        return redirect('http://127.0.0.1:5000/manual_upload')
    return redirect('http://127.0.0.1:5000/manual_upload')

if __name__ == "__main__":
  app.run(debug=False)


