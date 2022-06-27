# Part 3: Written Evaluation
## Question 1: 

To implement role based access control 
we would need to add 4 new tables. Role, User_Role, Permissions and a Role_Permissions table.

Role has columns, role_id, and role_name. where id is the primary key.

user_role is the table which stores the one to many relationship between our users table and our role table. 
this table has foreign keys user_id and role_id referencing the user and role tables respectively.

Permissions table has an id as it's primary key and a foreign key to the post_id column from the table posts.

the role_permission table stores which roles have permissions to access a resource.
it contains foreign keys to permission_id and role_id. 
additionally it contains columns can_add,can_edit,can_view,can_delete.
these columns specify which actions a role can perform on a specific resource.

to assign a user to a particular role,one would simply add a row to the users_role value

## Question 2:
 
In order to implement, we would need to check the role of the user before performing the query. Then before updating a post check in role_permissions table if the user's role has the proper permission to edit the post.
similarly, before adding or deleting a post, check if the user's role has permissions to perform the operation 
 before the query to the database. if the current role has sufficient permissions to access the given blog post perform the action.
if they do not we simply return an error with a message "unauthorized access" or something similar. 