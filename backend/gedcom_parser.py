import re

def parse_gedcom_content(content: str):
    lines = [line.rstrip("\n\r") for line in content.splitlines()]

    individuals = {}
    families = {}

    current_id = None
    current_type = None

    # 1) Première passe : on récupère les individus, familles, noms, liens bruts
    for line in lines:
        parts = line.split(" ", 2)

        if len(parts) == 3 and parts[0] == "0" and parts[1].startswith("@") and parts[2] in ("INDI", "FAM"):
            current_id = parts[1].strip("@")
            current_type = parts[2]

            if current_type == "INDI":
                individuals[current_id] = {
                    "id": current_id,
                    "name_raw": None,
                    "first_name": None,
                    "last_name": None,
                    "birth_date": None,
                    "birth_place": None,
                    "father_id": None,
                    "mother_id": None,
                    "family_as_child": None,
                }
            elif current_type == "FAM":
                families[current_id] = {
                    "id": current_id,
                    "husband_id": None,
                    "wife_id": None,
                    "children_ids": []
                }

            continue

        if current_type == "INDI":
            if line.startswith("1 NAME "):
                name_val = line[len("1 NAME "):]
                individuals[current_id]["name_raw"] = name_val
                m = re.match(r"([^/]+)/([^/]+)/?", name_val)
                if m:
                    individuals[current_id]["first_name"] = m.group(1).strip() or None
                    individuals[current_id]["last_name"] = m.group(2).strip() or None

            elif line.startswith("1 FAMC "):
                famc = line[len("1 FAMC "):].strip()
                famc = famc.strip("@")
                individuals[current_id]["family_as_child"] = famc

        elif current_type == "FAM":
            if line.startswith("1 HUSB "):
                husb = line[len("1 HUSB "):].strip().strip("@")
                families[current_id]["husband_id"] = husb
            elif line.startswith("1 WIFE "):
                wife = line[len("1 WIFE "):].strip().strip("@")
                families[current_id]["wife_id"] = wife
            elif line.startswith("1 CHIL "):
                child = line[len("1 CHIL "):].strip().strip("@")
                families[current_id]["children_ids"].append(child)

    # 2) Deuxième passe : extraire naissance (1 BIRT -> 2 DATE / 2 PLAC)
    current_id = None
    in_birth_block = False
    for line in lines:
        parts = line.split(" ", 2)

        if len(parts) == 3 and parts[0] == "0" and parts[1].startswith("@") and parts[2] == "INDI":
            current_id = parts[1].strip("@")
            in_birth_block = False
            continue

        if current_id is None:
            continue

        if line.startswith("1 BIRT"):
            in_birth_block = True
            continue

        if line.startswith("1 ") and not line.startswith("1 BIRT"):
            in_birth_block = False

        if in_birth_block:
            if line.startswith("2 DATE "):
                individuals[current_id]["birth_date"] = line[len("2 DATE "):].strip() or None
            elif line.startswith("2 PLAC "):
                individuals[current_id]["birth_place"] = line[len("2 PLAC "):].strip() or None

    # 3) Associer père/mère via la famille d'enfant
    for ind_id, ind in individuals.items():
        famc = ind["family_as_child"]
        if famc and famc in families:
            ind["father_id"] = families[famc]["husband_id"]
            ind["mother_id"] = families[famc]["wife_id"]

    return individuals, families