# GETFit

#### Description:
This is my final project for CS50. I have developed a web application that caters specifically to fitness enthusiasts. This application enables users to calculate their required calorie intake, body fat percentage, and calories burned during workouts. A distinctive feature of this application is its database system, which saves all relevant user information. Moreover, I have incorporated features that allow users to visualize and track their progress over time through slides. This project combines knowledge from computer science and fitness to create a tool that could significantly aid people in their fitness journey.

login_required: This is a decorator that checks if the user is authenticated. If not, the user is redirected to the login page.

after_request: This function ensures that the server's responses are not cached.

calories_history: This route gets the user's calorie intake history from the database and renders the template with the data.

training_results: This route fetches the user's training history and passes the data to the rendering template.

training_history: This route enables the user to record their training session and calculate the calories burned during that session.

bodyfat_history: This route fetches the user's body fat history and renders it in a template.

bodyfat: This route enables the user to calculate their body fat percentage and stores the result in the database.

index: This route simply renders the profile page.

cal_calc: This route handles the calorie calculation form. It takes the user's input, calculates the necessary caloric intake, and stores the result in the database.

change_password: This route enables the user to change their password. It checks if the old password is correct, if the new password and the confirmation match, and updates the password in the database.

register: This route handles the registration process. It validates the user's input and, if everything is correct, creates a new user in the database.

login: This route handles the login process. It checks if the entered username and password match the data in the database, and if so, logs the user in.

Each route decorated with @login_required requires the user to be authenticated. If the user is not authenticated, they are redirected to the login page.

Remember that the purpose of these routes is to manage HTTP requests and responses in a web application, providing functionality to the users.