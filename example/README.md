# Django DeepSerializer Example

In this this example will be every infromation about the basic usage of the DeepSerializer module.

## Prerequisites

- Docker

## Installation

```bash
docker-compose up -d --build
```

## Usage

The example is fully functional and you can access the API on `http://localhost:8000/`.

List of avaible endpoints :
- `HighSchool`: `http://localhost:8000/HighSchool/` Deep creation enabled
- `Student`: `http://localhost:8000/Student/` Deep creation disbaled
- `Class`: `http://localhost:8000/Class/` Deep creation enabled

Deep creation is enable and disable by the `secure` parameter in the used in `ModelInfo` object in the `urls.py` file.

## Example

### HighSchool endpoint

Example of a POST request to create a new HighSchool with a creation of two nested classes :

```bash
curl --location 'http://localhost:8000/HighSchool/' \
--header 'Content-Type: application/json' \
--header 'Cookie: csrftoken=XIVVTM6O7AyFkdi6UclbXu4qqzYMmx4X' \
--data '{
    "name": "Toulouse",
    "address": "Toulouse",
    "classes": [
        {
            "name": "1A"
        },
        {
            "name": "1B"
        }
    ]
}'
```

Example of a GET request to get a HighSchool with a depth of 1 to get the nested classes :

```bash
curl --location 'http://localhost:8000/HighSchool/?depth=1' \
--header 'Cookie: csrftoken=XIVVTM6O7AyFkdi6UclbXu4qqzYMmx4X'
```

### Class endpoint

Example of a POST request to create a new Class with a creation of a nested HighSchool and a nested Student :

```bash
curl --location 'http://localhost:8000/Class/' \
--header 'Content-Type: application/json' \
--header 'Cookie: csrftoken=XIVVTM6O7AyFkdi6UclbXu4qqzYMmx4X' \
--data '[
    {
        "name": "6°4",
        "high_school": {
            "name": "Bordeaux",
            "address": "Bordeaux"
        },
        "students":[
            {
                "name": "enzo",
                "age": 18
            }
            
        ]
    }
]'
```

Example of a GET request to get a Class with a depth of 1 to get the nested HighSchool and Student :

```bash
curl --location 'http://localhost:8000/Class/?depth=1' \
--header 'Cookie: csrftoken=XIVVTM6O7AyFkdi6UclbXu4qqzYMmx4X'
```

### Student endpoint

The student endpoint is secure as you can see in urls.py, so you cannot made nested creation with the Student endpoint. Because student are inferior !

urls.py extract :

```python
router = routers.DefaultRouter()
DeepViewSet.init_router(router, [
    ModelInfo(model=HighSchool, secure=False),
    ModelInfo(model=Student, secure=True),
    ModelInfo(model=Class, secure=False),
])
```

Usage of the endpoint are the same as other default endpoint Django REST framework endpoint but it give depth wiew with the depth parameter in the url.

## Development usage

If you want to develop on the DeepSerializer module, you can use modifiy the `Dockerfile` to start the container with an inifinite loop replacing the define line in the `Dockerfile`. 

```Dockerfile
CMD ["tail", "-f", "/dev/null"]
```
And then the module is accessible in the container in the `/deepserializer` folder. You can modify the code and then reinstall the modify module with the following command :

```bash
pip install /deepserializer
```