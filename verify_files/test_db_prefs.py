from storage import db
import time

user_id = "test_user_verify"

# 1. Clear
db.clear_user_pref(user_id)
assert db.get_user_pref(user_id) == {}
print("Clear Check Parent")

# 2. Set
db.set_user_pref(user_id, language="Hausa")
pref = db.get_user_pref(user_id)
assert pref['language'] == "Hausa"
print("Set Language Check Passed")

# 3. Update Mode
db.set_user_pref(user_id, interaction_mode="voice")
pref = db.get_user_pref(user_id)
assert pref['language'] == "Hausa"
assert pref['interaction_mode'] == "voice"
print("Update Mode Check Passed")

# 4. Clear
db.clear_user_pref(user_id)
assert db.get_user_pref(user_id) == {}
print("Final Clear Check Passed")

print("DB Verification SUCCESS")
