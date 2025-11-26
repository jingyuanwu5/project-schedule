# OR-TOOLS examples


# example1: A nurse scheduling problem
# In the next example, a hospital supervisor needs to create a schedule for four nurses over a three-day period, subject to the following conditions:

# Each day is divided into three 8-hour shifts.
# Every day, each shift is assigned to a single nurse, and no nurse works more than one shift.
# Each nurse is assigned to at least two shifts during the three-day period.
# The following sections present a solution to the nurse scheduling problem.

# example2: Scheduling with shift requests
# In this section, we take the previous example and add nurse requests for specific shifts. 
# We then look for a schedule that maximizes the number of requests that are met. For most scheduling 
# problems, it's best to optimize an objective function, as it is usually not practical to print 
# all possible schedules.
