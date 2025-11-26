# Library Review for Project Schedule
#   After researching four libraries, I gained a general understanding of their respective strengths, weaknesses,
#   and applications.
# Google OR-Tools:
#   Google OR-Tools is a free and open-source software suite, OR-Tools can solve constraint programming 
#   and have bundled CP-SAT Solver so that can handle complex constraints and It is particularly well-suited 
#   for scheduling classes, meetings, and assessments.Additionally, it supports multiple programming languages 
#   including Python, and comes with comprehensive tutorials and rich sample codes, making it highly valuable for reference.[1]
# OptaPlanner:
#   This library's functionality includes Agenda scheduling, Educational timetabling and scheduling other things 
#   but it main language is java,  which is incompatible with the Python I need to use.[2]
# CPMpy:
#   CPMpy is ideal for solving combinatorial problems like assignment problems or covering, packing and scheduling problems.
#   It also suit for this project. Through the reference I get CPMpy is open source, all discussions happen on GitHub,
#   then I searched the GitHub for tutorials and related examples of CPMpy, but found relatively few available resources.
#   In this regard, it falls short of OR-Tools.[3]
# PyJobShop:
#   This is a Python library for solving scheduling problems with constraint programming. But from the reference, 
#   It currently supports the following scheduling problems:
#     Resource environments: single machines, parallel machines, hybrid flow shops, open shops, job shops, flexible job 
#     shops, distributed shops, renewable resources and non-renewable resources.
#     Constraints: release dates, deadlines, due dates, multiple modes, permutations, sequence-dependent setup times, 
#     no-wait, no-idle, blocking, breaks, optional task selection, and arbitrary precedence constraints.
#     Objective functions: minimizing makespan, total flow time, number of tardy jobs, total tardiness, total earliness, 
#     maximum tardiness, and total setup times.
#   Based on the description in the above materials, this library primarily functions for shop operations and 
#   appears to have little relevance to the scheduling and timetable management requirements of our project.
# In summary, I think Google OR-Tools is the most suitable option.
#
#Reference:
# [1]OR-Tools https://en.wikipedia.org/wiki/OR-Tools
# [2]OptaPlanner User Guide https://docs.optaplanner.org/latestFinal/optaplanner-docs/html_single/
# [3]CPMpy: Constraint Programming and Modeling in Python https://cpmpy.readthedocs.io/en/latest/
