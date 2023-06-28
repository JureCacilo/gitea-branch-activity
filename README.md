# Gitea branch activity script
Reports the activity of branches of a given repository based on the gitea server, owner,
            repository and number of days of inactivity.
            Output is a table of branches where the last commit of the branch
            was more than the given number of inactive days.

To test the script run in the cmd: 
**python branch_activity_report.py --access_token --gitea_url --repo_owner --repository --number_of_days**
