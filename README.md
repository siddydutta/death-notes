# Death Notes
> COMPSCI5012 Internet Technology (M) 2024-25

![Build Status](https://github.com/siddydutta/death-notes/actions/workflows/tests.yml/badge.svg)
![Deployment Status](https://github.com/siddydutta/death-notes/actions/workflows/deploy.yml/badge.svg)


# Project Requirements
1. [Python 3.12](https://www.python.org/downloads/release/python-3120/)

# Project Setup
1. Clone the Project
```
git clone https://github.com/siddydutta/death-notes.git
cd death-notes/
```

2. Create & Activate Python Virtual Environment
```
python3.12 -m venv venv/
source venv/bin/activate  # For MacOS/Linux
venv\Scripts\activate  # For Windows
```

3. Install Requirements
```
pip install -r requirements.txt
```

4. Install Pre-Commit Hooks
```
pre-commit install
```

5. Create Superuser for Admin
```
python manage.py createsuperuser
```

6. Start Server and Cluster
```
python manage.py runserver
```
and
```
python manage.py qcluster
```

7. Tests and Coverage Reports
Run Test
```
coverage run manage.py test
```
Generate Report
```
coverage report -m
```
OR for a detailed HTML report:
```
coverage html
```


# Team Members
1. Arshia Kaul (2976917K@student.gla.ac.uk)
2. Harish Ravichandran (2973284R@student.gla.ac.uk)
3. Siddhartha Pratim Dutta (2897074D@student.gla.ac.uk)
