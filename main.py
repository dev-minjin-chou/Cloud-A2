from flask import Flask, render_template, request, url_for, redirect, send_file
import logging
import boto3
from botocore.exceptions import ClientError
import datetime


app = Flask(__name__)

username_login = ''
userid_login = ''
s3_client = boto3.client('s3')

@app.route("/")
def root():
    return render_template("login.html")

firebase_request_adapter = requests.Request() 
@app.route('/login', methods=["POST", "GET"])
def login():
    subjects = fetch_latestSub(10)

    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        error_msg = None

        try: 
            query = datastore_client.query(kind='user') 
            matches = list(query.add_filter('id', '=', user_id).fetch(1))

            if len(matches) > 0:
                match = matches[0]
                if user_id != match['id']:
                    error_msg = 'ID or password is invalid.'
                    return render_template('login.html', error_msg=error_msg)
                elif password != match['password']:
                    error_msg = 'ID or password is invalid.'
                    return render_template('login.html', error_msg=error_msg)
                else:
                    global username_login, userid_login
                    userid_login = match['id']
                    username_login = match['user_name']

                    test = os.path.join("https://storage.cloud.google.com/cloud-computinga-01.appspot.com/", userid_login)


                    return render_template('forum.html', username_login=username_login, subjects=subjects, test=test)
            else:
                error_msg = 'ID or password is invalid.'
                return render_template('login.html', error_msg=error_msg)

        except Exception as e:
            error_msg = e
        return render_template('login.html', error_msg=error_msg)
    else:
        return render_template('login.html')
        
@app.route('/register', methods=["POST", "GET"])
def register():

    if request.method == "POST":
        user_id = request.form.get("user_id")
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        error_msg = None
        file_img = request.files['file']

        try:
            query = datastore_client.query(kind='user')
            qry = datastore_client.query(kind='user')
            matches = list(query.add_filter('id', '=', user_id).fetch(1))
            usernames = list(qry.add_filter('user_name', '=', user_name).fetch(1))

            # To check for duplicates of id
            if len(matches) > 0:
                match = matches[0]
                if user_id == match['id']:
                    error_msg = 'The ID already exists.'
                    return render_template('register.html', error_msg=error_msg)
            
            # To check for duplicates of usernames
            if len(usernames) > 0:
                user = usernames[0]
                if user_name == user['user_name']:
                    error_msg = 'The username already exists.'
                    return render_template('register.html', error_msg=error_msg)
            
            if 'file' not in request.files:
                error_msg = 'No file error'
                return render_template('register.html', error_msg=error_msg)

            if file_img.filename == '':
                error_msg = 'Please choose a file to upload as user avatar.'
                return render_template('register.html', error_msg=error_msg)


            else:
                # Store new user entity
                entity = datastore.Entity(key=datastore_client.key('user')) 
                entity.update({ 'id': user_id, 
                                'user_name': user_name,
                                'password': password
                             }) 
                datastore_client.put(entity) 

                file_img.save('/tmp/' + file_img.filename)

                bucket = storage_client.get_bucket('cloud-computinga-01.appspot.com')
                blob = bucket.blob(user_id)
    
                #store image
                blob.upload_from_filename('/tmp/' + file_img.filename)
                return redirect(url_for("login"))

        except Exception as e:
            error_msg = e
        return render_template('register.html', error_msg=error_msg)

    else:
        return render_template('register.html')

if __name__ == '__main__':

    app.run(host='127.0.0.1', port=8080, debug=True)

