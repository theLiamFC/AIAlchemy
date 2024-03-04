import time
import requests

THREAD_ID = "thread_UbU1hougFO6WE4kJCmK0ylRR"

url = f"https://api.openai.com/v1/threads/{THREAD_ID}/runs/{RUN_ID}"

times = 20
timeout_count = 0
success_count = 0
sum_response_time = 0

for i in range(times):
    try:
        start_time = time.time()
        response = requests.get(url, headers=HEADERS, timeout=10)
        end_time = time.time()

        response_time = end_time - start_time
        sum_response_time += response_time
        success_count += 1
        print(f"Attempt {i+1}: Response time = {response_time} seconds")

    except requests.exceptions.Timeout:
        print(f"Attempt {i+1}: The request timed out after 10 seconds.")
        timeout_count += 1
    except requests.exceptions.RequestException as e:
        print(f"Attempt {i+1}: An error occurred: {e}")
    time.sleep(1)

print(f"Number of successful requests: {success_count}/{times}")
print(f"Number of timeouts: {timeout_count}/{times}")
print(f"Average response time: {sum_response_time/success_count} seconds")
