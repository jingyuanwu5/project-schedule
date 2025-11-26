# project-schedule
# Scheduling tool for project assessments
**Student**: Jingyuan Wu 22116320  
**Course**: CSC1049

# Project Overview
# This project aims to develop a user-friendly program for scheduling student project assessments (COMSCI3, COMSCI4, COMBUS4, DS4, and MCM). The system needs to handle different types of student projects while accounting for their unique requirements and constraints.

# Complete work

# 1.Library review and selection
  - Compared four libraries: Google OR-Tools, OptaPlanner, CPMpy and PyJobShop
  - Selected Google OR-Tools for its strong scheduling support and Python integration
  - Selected **Google OR-Tools** as the  tool
# 2. OR-Tools Learning
  - Completed basic tutorials and example programs
  - Notes stored in: tutorials/README.md
# 3. Data Format (JSON)
  - Designed JSON structures for lecturers, projects, and time slots
  - Examples in data/
  - Rationale explained in docs/data_format.md
# 4. Scheduling Requirements
  - Define basic roles and desirable properties
  - Two lecturers per project
  - Lecturer availability and lunch breaks
  - even spread of work across all lecturers
  - details in docs/scheduling_constraints.md
# 5. Basic Scheduler
  - simple example of the 4YP scheduler using OR-Tools
  - code in src/scheduling_4yp.py

