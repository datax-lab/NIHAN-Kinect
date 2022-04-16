import requests
import sched
import time

# Login a user and get the access and refresh tokens
#
# You need to send the access_token with each subsequent request.
# access_token is valid for 5 minutes, and will need to be refreshed using the refresh_token.
response = requests.post('https://www.healage.org/auth/login', json={
    'username': 'nihan',
    'password': 'nihan123',
})
data = response.json()
access_token = data['accessToken']

# Every 4 minutes you need to refresh the user's session.
# This is required for security reasons.
# If the session is not refreshed, subsequent requests using the access_token will not be authorized.
# Here I am using the sched module, but you can probably integrate with PyQt5 to setup this scheduled event.
REFRESH_INTERVAL = 5  # 4 minutes
s = sched.scheduler(time.time, time.sleep)


# This function will be called every 4 minutes and update the global response and access_token variables.
def refresh():
    global response, access_token
    print('refreshing token')
    response = requests.post('https://www.healage.org/auth/refresh', cookies=response.cookies)
    data = response.json()
    access_token = data['accessToken']
    s.enter(REFRESH_INTERVAL, 1, refresh)


s.enter(REFRESH_INTERVAL, 1, refresh)
s.run(blocking=False)

# Sending gait speed
gait_speed_data = {
    'patientId': '5HZK4BHT',
    'date': '2022-02-26',  # Date must be in this format yyyy-mm-dd
    'averageGaitSpeed': 1.0,
    'gaitSpeedResults': [  
            {   
                'Program Run' : 0,
                'Results' : 
                {
                    {
                        'time': 0,
                        'distance': 0,
                        'instantVelocity': 0,
                    },
                    {
                        'time': 1,
                        'distance': 1,
                        'instantVelocity': 1,
                    },
                    {
                        'time': 2,
                        'distance': 3,
                        'instantVelocity': 1.5,
                    },
                    {
                        'time': 3,
                        'distance': 6,
                        'instantVelocity': 2,
                    }, 
                }
            },
            
            {   
                'Program Run' : 0,
                'Results' : 
                {
                    {
                        'time': 0,
                        'distance': 0,
                        'instantVelocity': 0,
                    },
                    {
                        'time': 1,
                        'distance': 1,
                        'instantVelocity': 1,
                    },
                    {
                        'time': 2,
                        'distance': 3,
                        'instantVelocity': 1.5,
                    },
                    {
                        'time': 3,
                        'distance': 6,
                        'instantVelocity': 2,
                    }, 
                },
            },
    ],
}
res = requests.post('https://www.healage.org/api/kinect-gait-speed', json=gait_speed_data)
# Keep sending if the request doesn't go through -> or handle this however you would like to handle it.
while not res.ok:
    res = requests.post('https://www.healage.org/api/kinect-gait-speed', json=gait_speed_data)

# Sending kyphosis index
kyphosis_index_data = {
    'patientId': '5HZK4BHT',
    'date': '2022-02-26',  # Date must be in this format yyyy-mm-dd
    'kyphosisIndex': 22.0,
}
res = requests.post('https://www.healage.org/api/kyphosis-index', json=kyphosis_index_data)
# Keep sending if the request doesn't go through -> or handle this however you would like to handle it.
while not res.ok:
    res = requests.post('https://www.healage.org/api/kyphosis-index', json=kyphosis_index_data)

# Logout at the end of the program
requests.post('https://www.healage.org/auth/logout', cookies=response.cookies)
