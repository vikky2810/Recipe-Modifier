import os
import json

from app import app, user_manager


def ensure_test_user():
    # Create or fetch a stable test user
    test_username = "testuser_auth"
    user = user_manager.get_user_by_username(test_username)
    if user:
        return user.user_id
    user, error = user_manager.create_user(
        username=test_username,
        email="testuser_auth@example.com",
        password="Password123!",
        medical_condition="diabetes",
    )
    if not user:
        raise RuntimeError(f"Failed to create test user: {error}")
    return user.user_id


def run_tests():
    test_user_id = ensure_test_user()
    results = {}

    with app.test_client() as client:
        # 1) Unauthenticated: should redirect (302) to login
        r1 = client.get(f"/generate_report/1", follow_redirects=False)
        results["unauthenticated_generate_report_status"] = r1.status_code
        results["unauthenticated_generate_report_location"] = r1.headers.get("Location")

        # 2) Logged in as test user, request other patient's report => 403
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user_id)
        r2 = client.get("/generate_report/1")
        results["mismatched_generate_report_status"] = r2.status_code

        # 3) Logged in as test user, request own report => expect 200 or 400
        # 200 if PDF generated successfully, else 400 if it fails; both prove auth gate works
        r3 = client.get(f"/generate_report/{test_user_id}")
        results["matched_generate_report_status"] = r3.status_code

        # 4) Same checks for view_report
        with client.session_transaction() as sess:
            sess["_user_id"] = None
        r4 = client.get(f"/view_report/1", follow_redirects=False)
        results["unauthenticated_view_report_status"] = r4.status_code
        results["unauthenticated_view_report_location"] = r4.headers.get("Location")

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user_id)
        r5 = client.get("/view_report/1")
        results["mismatched_view_report_status"] = r5.status_code

        r6 = client.get(f"/view_report/{test_user_id}")
        results["matched_view_report_status"] = r6.status_code

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run_tests()


