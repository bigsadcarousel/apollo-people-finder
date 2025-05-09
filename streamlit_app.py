import streamlit as st
import pandas as pd
import requests
import math
import io
import time

st.title("Apollo People Finder")

# 1. Upload CSV
data_file = st.file_uploader("Upload comp_data.csv with company websites", type=["csv"])

# 2. Enter Apollo API key
default_apollo_key = st.secrets["APOLLO_API_KEY"] if "APOLLO_API_KEY" in st.secrets else ""
api_key = st.text_input("Enter your Apollo API key", value=default_apollo_key, type="password")

# 2b. Enter MillionVerifier API key
default_mv_key = st.secrets["MV_API_KEY"] if "MV_API_KEY" in st.secrets else ""
mv_api_key = st.text_input("Enter your MillionVerifier API key", value=default_mv_key, type="password")

# 3. Enter job titles (comma or newline separated)
titles_input = st.text_area("Enter job titles (one per line or comma separated)")

def parse_titles(titles_str):
    if not titles_str:
        return []
    if "," in titles_str:
        return [t.strip() for t in titles_str.split(",") if t.strip()]
    return [t.strip() for t in titles_str.splitlines() if t.strip()]

def get_apollo_data(page, companies, titles, api_key):
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": api_key,
        "q_organization_domains": companies,
        "page": page,
        "per_page": 100,
        "person_titles": titles
    }
    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    total_page = int(math.ceil(result['pagination']['total_entries'] / 200))
    return result, total_page

def generate_email_combinations(first, last, domain):
    first = first.lower() if first else ''
    last = last.lower() if last else ''
    domain = domain.lower() if domain else ''
    combos = set()
    if first and last and domain:
        combos.update([
            f"{first}.{last}@{domain}",
            f"{first}{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{first[0]}.{last}@{domain}",
            f"{first}_{last}@{domain}",
            f"{first[0]}_{last}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{first[0]}{last[0]}@{domain}",
        ])
    return list(combos)

def verify_email_millionverifier(email, mv_api_key):
    url = f"https://api.millionverifier.com/api/v3/?api={mv_api_key}&email={email}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Return tuple of (status, email) if verification successful
        if data.get('result') in ['ok', 'catch-all', 'accept']:
            return True, email
        return False, None
    except Exception as e:
        st.error(f"Error verifying {email}: {str(e)}")
        return False, None

if data_file and api_key and titles_input and mv_api_key:
    df = pd.read_csv(data_file)
    if 'company_web_url' in df.columns:
        companies = df['company_web_url'].dropna().unique().tolist()
    elif 'comp_web_url' in df.columns:
        companies = df['comp_web_url'].dropna().unique().tolist()
    else:
        st.error("CSV must have a 'company_web_url' or 'comp_web_url' column.")
        st.stop()

    titles = parse_titles(titles_input)
    st.write(f"Found {len(companies)} companies and {len(titles)} titles.")

    if st.button("Find People and Verify Emails"):
        people_list = []
        progress = st.progress(0)
        status_container = st.empty()
        verification_container = st.empty()
        
        for idx, chunk_start in enumerate(range(0, len(companies), 20)):
            comps_chunk = companies[chunk_start:chunk_start+20]
            companies_str = '\n'.join(comps_chunk)
            try:
                status_container.write(f"Processing companies {chunk_start} to {chunk_start+20}")
                response, total_pages = get_apollo_data(1, companies_str, titles[:99], api_key)
                
                for person in response.get('people', []):
                    first = person.get('first_name')
                    last = person.get('last_name')
                    
                    # Get domain from organization website or comp_web_url
                    domain = ''
                    if person.get('organization') and person['organization'].get('website_url'):
                        domain = person['organization']['website_url'].replace('https://','').replace('http://','').replace('www.','').split('/')[0]
                    elif person.get('comp_web_url'):
                        domain = person['comp_web_url'].replace('https://','').replace('http://','').replace('www.','').split('/')[0]
                    
                    verified_email = None
                    verified_status = 'not_verified'
                    
                    if first and last and domain:
                        verification_container.write(f"Verifying emails for {first} {last} at {domain}")
                        emails = generate_email_combinations(first, last, domain)
                        
                        for email in emails:
                            verification_container.write(f"Trying {email}...")
                            is_valid, valid_email = verify_email_millionverifier(email, mv_api_key)
                            if is_valid:
                                verified_email = valid_email
                                verified_status = 'verified'
                                verification_container.write(f"✅ Found valid email: {valid_email}")
                                break
                            time.sleep(1)  # Rate limiting
                    
                    p_dict = {
                        'id': person.get('id'),
                        'first_name': first,
                        'last_name': last,
                        'linkedin': person.get('linkedin_url'),
                        'title': person.get('title'),
                        'email_status': person.get('email_status'),
                        'apollo_email': person.get('email'),
                        'verified_email': verified_email,
                        'verification_status': verified_status,
                        'country': person.get('country'),
                        'company': person['employment_history'][0]['organization_name'] if person.get('employment_history') else '',
                        'company_title': person['employment_history'][0]['title'] if person.get('employment_history') else '',
                        'comp_web_url': domain
                    }
                    people_list.append(p_dict)
                    
            except Exception as e:
                st.warning(f"Error for chunk {chunk_start}: {e}")
            
            progress.progress((idx+1)/math.ceil(len(companies)/20))
        
        verification_container.empty()
        status_container.empty()
        
        if people_list:
            people_df = pd.DataFrame(people_list).drop_duplicates()
            
            # Show verification stats
            total = len(people_df)
            verified_df = people_df[people_df['verification_status'] == 'verified'].copy()
            verified = len(verified_df)
            st.write(f"Found {total} people, verified emails for {verified} ({(verified/total*100):.1f}%)")
            
            # Show the dataframe with verified emails first
            people_df = people_df.sort_values('verification_status', ascending=False)
            st.dataframe(people_df)
            
            # Download buttons side by side
            col1, col2 = st.columns(2)
            
            with col1:
                # Download all results
                all_csv = people_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download All Results (CSV)", 
                    data=all_csv, 
                    file_name="all_results.csv", 
                    mime="text/csv",
                    help=f"Download all {total} results"
                )
            
            with col2:
                if not verified_df.empty:
                    # Download verified only
                    verified_csv = verified_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download Verified Only (CSV)", 
                        data=verified_csv, 
                        file_name="verified_emails.csv", 
                        mime="text/csv",
                        help=f"Download {verified} verified emails only"
                    )
                else:
                    st.info("No verified emails found")
        else:
            st.info("No people found for the given companies and titles.") 