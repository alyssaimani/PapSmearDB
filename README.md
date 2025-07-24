## Requirements

- python 3.10
- Install dependencies:
```pip install -r requirements.txt```

## Setup Instructions

1. Configure Environment Variables
   Create a ```.env``` file with the following variables:
    ``SECRET_KEY=YOUR_KEY``
    
    ``DB_NAME=YOUR_DB_NAME`` 
    
    ``DB_USER=YOUR_DB_USER``
    
    ``DB_PASS=YOUR_DB_PASS``
   To generate a secure SECRET_KEY, run

	"python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())”

2. Apply Migrations
   ```python manage.py makemigrations```

   ```python manage.py migrate```

5. Create Superuser

	```python manage.py createsuperuser```
