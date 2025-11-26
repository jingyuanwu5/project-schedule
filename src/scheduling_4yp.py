from ortools.sat.python import cp_model

def main():
    num_lecturers = 3
    num_projects = 5
    num_time_slots = 10

    model = cp_model.CpModel()

    assignments = {}
    for p in range(num_projects):
        for n in range(num_lecturers):
            for i in range(num_time_slots):
                assignments[(p, n, i)] = model.new_bool_var(f'assign_p{p}_n{n}_{i}')

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status == cp_model.OPTIMAL or if status == cp_model.OPTIMAL:
        print("Found a schedule")
    else:
        print("No schedule found")

if __name__ == "__main__":
    main()
