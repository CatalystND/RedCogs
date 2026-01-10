import requests
from bs4 import BeautifulSoup

def get_bristol_conditions():
    url = "https://www.bristolmountain.com/conditions/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table')

    if len(tables) < 2:
        print("Could not find both lift and trail tables.")
        return None, None

    # --- 1. EXTRACT LIFTS ---
    lifts = []
    lift_table = tables[0]
    for row in lift_table.find_all('tr')[1:]:  # Skip header
        cols = row.find_all('td')
        if len(cols) >= 2:
            lifts.append({
                "Name": cols[0].get_text(strip=True),
                "Status": cols[1].get_text(strip=True).upper()
            })

    # --- 2. EXTRACT TRAILS ---
    trails = []
    # Trail tables are usually the subsequent tables (Alpine Trails)
    for trail_table in tables[1:]:
        # Try to find difficulty from a preceding header or an icon in the table
        current_difficulty = "Unknown"
        header = trail_table.find_previous(['h3', 'h4', 'strong'])
        if header:
            header_text = header.get_text().lower()
            if "easier" in header_text: current_difficulty = "● Easier"
            elif "more difficult" in header_text: current_difficulty = "■ More Difficult"
            elif "most difficult" in header_text: current_difficulty = "♦ Most Difficult"
            elif "extremely difficult" in header_text: current_difficulty = "♦♦ Extremely Difficult"

        for row in trail_table.find_all('tr'):
            cols = row.find_all('td')
            # Look for rows with Trail Name, Status, Surface, Comments
            if len(cols) >= 3:
                name = cols[0].get_text(strip=True)
                # Filter out header rows
                if name.lower() in ["trail", "lift", "status"]:
                    continue
                
                status = cols[1].get_text(strip=True).upper()
                surface = cols[2].get_text(strip=True) if len(cols) > 2 else "N/A"
                comments = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                # Double check for difficulty icons in the first cell
                img = cols[0].find('img')
                if img and img.get('alt'):
                    current_difficulty = img.get('alt')

                trails.append({
                    "Name": name,
                    "Difficulty": current_difficulty,
                    "Status": status,
                    "Conditions": f"{surface} {comments}".strip()
                })

    return lifts, trails

def display_results(lifts, trails):
    # Display Lifts
    print("\n" + "="*40)
    print(f"{'SKI LIFT STATUS':^40}")
    print("="*40)
    print(f"{'Lift Name':<30} | {'Status'}")
    print("-" * 40)
    for lift in lifts:
        icon = "✅" if lift['Status'] == "OPEN" else "❌"
        print(f"{lift['Name']:<30} | {icon} {lift['Status']}")

    # Display Trails
    print("\n" + "="*85)
    print(f"{'TRAIL CONDITIONS':^85}")
    print("="*85)
    print(f"{'Trail Name':<25} | {'Difficulty':<20} | {'Status':<8} | {'Conditions'}")
    print("-" * 85)
    for trail in trails:
        icon = "✅" if trail['Status'] == "OPEN" else "❌"
        print(f"{trail['Name']:<25} | {trail['Difficulty']:<20} | {icon} {trail['Status']:<8} | {trail['Conditions']}")

if __name__ == "__main__":
    print("Fetching Bristol Mountain Mountain Report...")
    lifts, trails = get_bristol_conditions()
    if lifts and trails:
        display_results(lifts, trails)
