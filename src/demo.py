from typing import Union
from ortools.sat.python import cp_model
import json


def main() -> None:
    with open('data/lecturers.json') as f:
        lecturers = json.load(f)['lecturers']
    with open('data/projects.json') as f:
        projects = json.load(f)['projects']
    with open('data/time_slots.json') as f:
        time_slots = json.load(f)['time_slots']
    
    num_lecturers = len(lecturers)
    num_projects = len(projects)
    num_slots = len(time_slots)
    
    all_lecturers = range(num_lecturers)
    all_projects = range(num_projects)
    all_slots = range(num_slots)
    
    model = cp_model.CpModel()
    
    assignments = {}
    for p in all_projects:
        for l in all_lecturers:
            for t in all_slots:
                assignments[(p, l, t)] = model.new_bool_var(f"p{p}_l{l}_t{t}")
    
    for p in all_projects:
        model.add(sum(assignments[(p, l, t)]
                     for l in all_lecturers
                     for t in all_slots) == 2
                 )
    
    project_time = {}
    for p in all_projects:
        project_time[p] = model.new_int_var(0, num_slots - 1, f"p{p}_time")

    for p in all_projects:
        model.add(sum(assignments[(p, l, t)] for l in all_lecturers for t in all_slots) == 2)

    for p in all_projects:
        for l in all_lecturers:
            for t in all_slots:
                model.add(project_time[p] == t).only_enforce_if(assignments[(p, l, t)])

    for l in all_lecturers:
        for t in all_slots:
            model.add_at_most_one(assignments[(p, l, t)] for p in all_projects)
    
    for p in all_projects:
        sup_id = projects[p]['supervisor']
        sup_idx = next(i for i, lec in enumerate(lecturers) if lec['id'] == sup_id)
        for t in all_slots:
            model.add(assignments[(p, sup_idx, t)] == 0)
    
    for l in all_lecturers:
        for t in lecturers[l]['unavailable']:
            for p in all_projects:
                model.add(assignments[(p, l, t)] == 0)
    
    total = num_projects * 2
    min_per_lec = total // num_lecturers
    max_per_lec = min_per_lec + (1 if total % num_lecturers else 0)
    
    for l in all_lecturers:
        num_assigned: Union[cp_model.LinearExpr, int] = 0
        for p in all_projects:
            for t in all_slots:
                num_assigned += assignments[(p, l, t)]
        model.add(min_per_lec <= num_assigned)
        model.add(num_assigned <= max_per_lec)
    
    first_slot = model.new_int_var(0, num_slots - 1, "first")
    last_slot = model.new_int_var(0, num_slots - 1, "last")
    
    for t in all_slots:
        slot_used = model.new_bool_var(f"slot{t}_used")
        model.add(sum(assignments[(p, l, t)] 
                     for p in all_projects 
                     for l in all_lecturers) >= 1).only_enforce_if(slot_used)
        model.add(first_slot <= t).only_enforce_if(slot_used)
        model.add(last_slot >= t).only_enforce_if(slot_used)
    
    span = model.new_int_var(0, num_slots, "span")
    model.add(span == last_slot - first_slot)
    model.minimize(span)
    
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    
    if status == cp_model.OPTIMAL:
        print("Solution:")
        print("=" * 60)
        
        for t in all_slots:
            projects_at_t = []
            for p in all_projects:
                lecs = [l for l in all_lecturers if solver.value(assignments[(p, l, t)]) == 1]
                if lecs:
                    projects_at_t.append((p, lecs))
            
            if projects_at_t:
                print(f"\n{time_slots[t]['day']} {time_slots[t]['time']}")
                print("-" * 60)
                for p, lecs in projects_at_t:
                    print(f"  {projects[p]['id']}: {projects[p]['student']}")
                    if len(lecs) == 2:
                        print(f"    {lecturers[lecs[0]]['name']}, {lecturers[lecs[1]]['name']}")
        
        print("\n" + "=" * 60)
        print(f"Time span: {solver.objective_value} slots")
        
        print("\nWorkload:")
        for l in all_lecturers:
            count = sum(solver.value(assignments[(p, l, t)]) 
                       for p in all_projects for t in all_slots)
            print(f"  {lecturers[l]['name']}: {count}")
        
    else:
        print("No optimal solution found!")
    

if __name__ == "__main__":
    main()
