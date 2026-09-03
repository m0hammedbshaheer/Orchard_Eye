from access_core import approve_request, list_pending_requests, reject_request


def main():
    print("\n=== OrchardEye API Request Manager ===\n")
    requests = list_pending_requests()

    if not requests:
        print("No API key requests found.")
        return

    for req in requests:
        print(f"[{req['id']}] {req['email']} - {req['status']} ({req['created_at']})")

    print("\nEnter a request ID to approve, or type reject <id> to reject.")
    action = input("Action: ").strip()

    if not action:
        return

    if action.lower().startswith("reject"):
        parts = action.split()
        if len(parts) != 2 or not parts[1].isdigit():
            print("Usage: reject <request_id>")
            return
        request_id = int(parts[1])
        try:
            reject_request(request_id)
            print(f"Request {request_id} rejected.")
        except ValueError as exc:
            print(exc)
        return

    if not action.isdigit():
        print("Enter a numeric request ID or 'reject <id>'.")
        return

    request_id = int(action)
    try:
        result = approve_request(request_id)
        print("\nRequest approved.")
        print(f"User ID : {result['user_id']}")
        print(f"API Key : {result['api_key']}")
        if result["emailed"]:
            print(f"Email sent to {result['email']}.")
        else:
            print("Email was not sent. Check database/email_logs.txt for credentials.")
    except ValueError as exc:
        print(exc)


if __name__ == "__main__":
    main()
