Step 1
Create a file `secret.txt` and add mysql username and password as comma separated values<br>eg: root,password

Step 2 (optional)
Enter the anaconda virtual env created
`conda activate (name)`

Step 3
Install all requirements
`pip install -r requirements.txt`
If any new library is installed make sure to update
`pip list --format=freeze > requirements.txt`

Step 4
Download the pkl file from colab

Step 5
`python app.py`