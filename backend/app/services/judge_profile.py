"""Name corrections preserve judge identity and require a fresh conflict review."""


def change_name(judge, first_name, last_name):
    if (judge.First_Name, judge.Last_Name) == (first_name, last_name):
        return False
    if not judge.Conflict_Review_Required:
        judge.Previous_Name = f"{judge.First_Name} {judge.Last_Name}"
    judge.First_Name = first_name
    judge.Last_Name = last_name
    judge.Name_Confirmed_At = None
    judge.Conflict_Review_Required = True
    return True
