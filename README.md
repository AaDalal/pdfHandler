# pdfHandler 

## ... is ...
A simple web editor to reorganize and merge pdf files.


## ... is made with ...
* Flask
* Javascript
* Bootstrap

## ... can be run by ...
Following these steps (assuming you are familiar with Python, a package manager (pip or conda), and have set the appropriate environment variables to make the direct calls of flask work.
1. Set up a python environment with the following: Python 3.7(+), Flask, pdf2image, PyPDF
2. Set the appropriate environment variables: (see [HERE](https://flask.palletsprojects.com/en/2.0.x/config/) for how to set flask's env variables outside of powershell)
```pwsh
$env:FLASK_APP = "flaskr"
$env:FLASK_ENV = "development"
flask run
```

## ... helped me learn ...
* The core web technologies underlying nearly all websites (GET, POST)
* Javascript
* Passing things between flask and Javascript through POST and templating
* Using bootstrap
