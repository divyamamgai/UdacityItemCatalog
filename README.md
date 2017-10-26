Item Catalog
===

This web application allows you to catalog items based on categories.

* User can login using Google Plus or Facebook.
* Only logged in users can create, edit or delete items.
* Only the creator of an item can perform edit and delete operations.
* Catalog can be viewed publicly.

Required Libraries
---
* httplib2 (0.10.3)
* SQLAlchemy (1.1.14)
* Flask (0.12.2)
* google_api_python_client (1.6.4)

Project Contents
---

```
.
├── app.py
├── catalog.db
├── database_setup.py
├── database_setup.pyc
├── facebook_client_secret.json
├── google_client_secret.json
├── README.md
├── requirements.txt
├── static
│   ├── css
│   │   ├── bootstrap-grid.min.css
│   │   ├── font-awesome.min.css
│   │   ├── main.css
│   │   └── main.min.css
│   ├── drawable
│   │   ├── png
│   │   │   ├── catalog-1024.png
│   │   │   ├── catalog-120.png
│   │   │   └── catalog.png
│   │   └── svg
│   │       └── catalog.svg
│   ├── fonts
│   │   ├── FontAwesome.otf
│   │   ├── fontawesome-webfont.eot
│   │   ├── fontawesome-webfont.svg
│   │   ├── fontawesome-webfont.ttf
│   │   ├── fontawesome-webfont.woff
│   │   └── fontawesome-webfont.woff2
│   └── js
│       ├── jquery.min.js
│       ├── login_facebook.js
│       ├── login_facebook.min.js
│       ├── login_google.js
│       ├── login_google.min.js
│       ├── main.js
│       └── main.min.js
└── templates
    ├── catalog_create.html
    ├── catalog.html
    ├── catalog_item_delete.html
    ├── catalog_item_edit.html
    ├── catalog_item.html
    ├── catalog_items_create.html
    ├── catalog_items.html
    ├── login.html
    └── main.html

9 directories, 39 files
```

Installation
---

#### OAuth Service Setup

* ##### Google
    Download the OAuth 2.0 credentials in json format from your project's 
    developer console and rename it as ```google_client_secret.json``` in the 
    root folder of the app.

* ##### Facebook
    Edit the ```facebook_client_secret.json``` file and replace the 
    ```app_id``` and ```app_secret``` fields with your app specific details.
    
#### Installing Dependencies
To install dependencies of this app simply run the following command if 
```pip``` is installed in your system. Otherwise check the Required Libraries 
section and install them manually.
```
pip -r requirements.txt
```

Operation
---
#### How to create database?
The application uses sqlite database. To create the database execute the 
following command from the app's root directory.
```
python database_setup.py
```
#### How to populate database?

**Database Structure**
It has following tables:
* category
```sqlite
CREATE TABLE category (
        id INTEGER NOT NULL,
        name VARCHAR(250) NOT NULL,
        user_id INTEGER,
        PRIMARY KEY (id),
        UNIQUE (name),
        FOREIGN KEY(user_id) REFERENCES user (id)
);
```
* item
```sqlite
CREATE TABLE item (
        id INTEGER NOT NULL,
        title VARCHAR(250) NOT NULL,
        description TEXT NOT NULL,
        category_id INTEGER,
        user_id INTEGER,
        PRIMARY KEY (id),
        UNIQUE (title),
        FOREIGN KEY(category_id) REFERENCES category (id),
        FOREIGN KEY(user_id) REFERENCES user (id)
);
```
* user
```sqlite
CREATE TABLE user (
        id INTEGER NOT NULL,
        name VARCHAR(250) NOT NULL,
        email VARCHAR(250) NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (email)
);
```

One can execute direct sql queries on the database using ```sqlite``` as 
follows:
```
sqlite3 catalog.db
```
This will give as interactive sqlite shell for the database.

#### How to run?
Execute the following command in your terminal:
```
python app.py
```

This will start the server at port 5000. Then simply open the following link 
in your browser - [http://localhost:5000](http://localhost:5000)

Vagrant is already configured to forward port 5000 to host machine.