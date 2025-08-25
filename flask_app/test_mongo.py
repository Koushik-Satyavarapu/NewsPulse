from pymongo import MongoClient
client = MongoClient('mongodb+srv://newspulse_user:CurBW0rHpZ3sOTKj@ac-97plfyc.oocp1sv.mongodb.net/newspulse_db?retryWrites=true&w=majority', serverSelectionTimeoutMS=30000)
print(client.admin.command('ping'))  # Should print {'ok': 1}

sai venkat
dharshini
