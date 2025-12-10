from collections import defaultdict

def find_duplicates(individuals):
    groups = defaultdict(list)

    for ind in individuals.values():
        first = (ind["first_name"] or "").strip().lower()
        last = (ind["last_name"] or "").strip().lower()
        birth = (ind["birth_date"] or "").strip().lower()

        # Ignorer les fiches totalement vides
        if first == "" and last == "" and birth == "":
            continue

        key = (first, last, birth)
        groups[key].append(ind)

    duplicates_report = []

    for key, people in groups.items():
        if len(people) > 1:
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    a = people[i]
                    b = people[j]

                    same_parents = (
                        a["father_id"] == b["father_id"]
                        and a["mother_id"] == b["mother_id"]
                        and a["father_id"] is not None
                    )

                    duplicates_report.append({
                        "a_id": a["id"],
                        "b_id": b["id"],
                        "first_name": a["first_name"] or "",
                        "last_name": a["last_name"] or "",
                        "birth_date": a["birth_date"] or "",
                        "birth_place_a": a["birth_place"] or "",
                        "birth_place_b": b["birth_place"] or "",
                        "same_parents": same_parents,
                    })

    return duplicates_report