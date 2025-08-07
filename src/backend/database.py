"""
MongoDB database configuration and setup for Mergington High School API
"""

from argon2 import PasswordHasher
import copy

# In-memory storage for development (when MongoDB is not available)
USE_MONGODB = False
try:
    from pymongo import MongoClient
    # Try to connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
    # Test the connection
    client.admin.command('ping')
    db = client['mergington_high']
    activities_collection = db['activities']
    teachers_collection = db['teachers']
    USE_MONGODB = True
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection failed: {e}. Using in-memory storage.")
    USE_MONGODB = False
if not USE_MONGODB:
    _activities_data = {}
    _teachers_data = {}
    
    class MockCollection:
        def __init__(self, data_store):
            self.data = data_store
        
        def count_documents(self, query):
            return len(self.data)
        
        def insert_one(self, document):
            doc_id = document.get('_id')
            if doc_id:
                self.data[doc_id] = {k: v for k, v in document.items() if k != '_id'}
        
        def find_one(self, query):
            if isinstance(query, dict) and '_id' in query:
                doc_id = query['_id']
                if doc_id in self.data:
                    result = copy.deepcopy(self.data[doc_id])
                    result['_id'] = doc_id
                    return result
            return None
        
        def find(self, query=None):
            result = []
            for doc_id, doc_data in self.data.items():
                doc = copy.deepcopy(doc_data)
                doc['_id'] = doc_id
                
                # Simple query matching
                if query is None or self._match_query(doc, query):
                    result.append(doc)
            return result
        
        def _match_query(self, doc, query):
            # Simple query matching for basic filters
            for key, value in query.items():
                # Handle nested field paths like "schedule_details.days"
                if '.' in key:
                    field_parts = key.split('.')
                    current_val = doc
                    for part in field_parts:
                        if isinstance(current_val, dict) and part in current_val:
                            current_val = current_val[part]
                        else:
                            return False
                    
                    # Now check the value against current_val
                    if isinstance(value, dict):
                        if '$in' in value:
                            if not any(item in current_val for item in value['$in']):
                                return False
                        elif '$gte' in value:
                            if current_val < value['$gte']:
                                return False
                        elif '$lte' in value:
                            if current_val > value['$lte']:
                                return False
                    else:
                        if current_val != value:
                            return False
                else:
                    # Handle top-level fields
                    if key in doc:
                        if isinstance(value, dict):
                            if '$in' in value:
                                if not any(item in doc[key] for item in value['$in']):
                                    return False
                            elif '$gte' in value:
                                if doc[key] < value['$gte']:
                                    return False
                            elif '$lte' in value:
                                if doc[key] > value['$lte']:
                                    return False
                        else:
                            if doc[key] != value:
                                return False
                    else:
                        return False
            return True
        
        def update_one(self, query, update):
            if isinstance(query, dict) and '_id' in query:
                doc_id = query['_id']
                if doc_id in self.data:
                    if '$push' in update:
                        for field, value in update['$push'].items():
                            if field in self.data[doc_id]:
                                self.data[doc_id][field].append(value)
                            else:
                                self.data[doc_id][field] = [value]
                    if '$pull' in update:
                        for field, value in update['$pull'].items():
                            if field in self.data[doc_id] and value in self.data[doc_id][field]:
                                self.data[doc_id][field].remove(value)
                    return type('MockResult', (), {'modified_count': 1})()
            return type('MockResult', (), {'modified_count': 0})()
        
        def aggregate(self, pipeline):
            # Simple aggregation for getting unique days
            result = set()
            for doc_data in self.data.values():
                if 'schedule_details' in doc_data and 'days' in doc_data['schedule_details']:
                    for day in doc_data['schedule_details']['days']:
                        result.add(day)
            return [{'_id': day} for day in sorted(result)]

    activities_collection = MockCollection(_activities_data)
    teachers_collection = MockCollection(_teachers_data)

# Methods
def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)

def init_database():
    """Initialize database if empty"""

    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in initial_activities.items():
            activities_collection.insert_one({"_id": name, **details})
            
    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in initial_teachers:
            teachers_collection.insert_one({"_id": teacher["username"], **teacher})

# Initial database if empty
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    },
    "Manga Maniacs": {
        "description": "Explore the fantastic stories of the most interesting characters from Japanese Manga (graphic novels).",
        "schedule": "Tuesdays, 7:00 PM - 8:30 PM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "19:00",
            "end_time": "20:30"
        },
        "max_participants": 15,
        "participants": []
    }
}

initial_teachers = [
    {
        "username": "mrodriguez",
        "display_name": "Ms. Rodriguez",
        "password": hash_password("art123"),
        "role": "teacher"
     },
    {
        "username": "mchen",
        "display_name": "Mr. Chen",
        "password": hash_password("chess456"),
        "role": "teacher"
    },
    {
        "username": "principal",
        "display_name": "Principal Martinez",
        "password": hash_password("admin789"),
        "role": "admin"
    }
]

