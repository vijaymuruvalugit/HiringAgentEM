import streamlit as st
import pandas as pd
import requests
import os
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Sourcing Quality Agent",
    page_icon="📊",
    layout="wide"
)

st.title("Hiring Tracker")
st.write("Upload your hiring tracker CSV to see sourcing channel quality summary.")

# n8n endpoint configuration
DEFAULT_WEBHOOK_URL = "http://localhost:5678/webhook-test/35f7df3a-1934-4e5f-82ac-cdedd7cb99e7"

# Get webhook URL from environment, secrets, or use default
n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL', '')
if not n8n_webhook_url:
    try:
        n8n_webhook_url = st.secrets.get('n8n_webhook_url', DEFAULT_WEBHOOK_URL)
    except (AttributeError, FileNotFoundError, TypeError):
        n8n_webhook_url = DEFAULT_WEBHOOK_URL

# Allow override in sidebar if needed
webhook_override = st.sidebar.text_input(
    "n8n Webhook URL (optional override)",
    value=n8n_webhook_url,
    key="webhook_url_override",
    help="Override the default n8n webhook URL if needed"
)
# Use sidebar value if provided
if webhook_override:
    n8n_webhook_url = webhook_override

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    if not n8n_webhook_url:
        st.error("Please configure the n8n webhook URL in the sidebar.")
        st.stop()
    
    # Show loading state
    with st.spinner("Processing CSV with n8n agent..."):
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Prepare file for upload
            files = {
                'file': (uploaded_file.name, uploaded_file, 'text/csv')
            }
            
            # Send CSV to n8n webhook
            response = requests.post(
                n8n_webhook_url,
                files=files,
                timeout=60  # 60 second timeout
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse JSON response from n8n
            try:
                result_data = response.json()
                
                # Debug: Show raw response (can be removed later)
                with st.expander("🔍 Debug: View Raw Response", expanded=False):
                    st.json(result_data)
                
                # Check if n8n returned async response
                if isinstance(result_data, dict) and 'message' in result_data:
                    if 'started' in result_data.get('message', '').lower():
                        st.error("⚠️ n8n workflow is running asynchronously")
                        st.markdown("""
                        **The webhook returned a 'started' message instead of data.**
                        
                        **To fix this in n8n:**
                        1. Add a **"Respond to Webhook"** node after your "Code in JavaScript" node
                        2. Connect the Code node output to the Respond to Webhook node
                        3. In the Respond to Webhook node settings:
                           - Set **Response Mode** to "Using 'Respond to Webhook' Node"
                           - Set **Response Data** to "All Incoming Items"
                        4. Make sure the webhook node is set to wait for the response
                        
                        Alternatively, you can configure the webhook node to:
                        - Set **Response Mode** to "Last Node" or "When Last Node Finishes"
                        """)
                        st.stop()
                
                # n8n returns array of items, each item has json property
                if isinstance(result_data, list) and len(result_data) > 0:
                    # Extract all records from n8n format: [{json: {...}}, {json: {...}}, ...]
                    all_records = []
                    
                    for item in result_data:
                        if isinstance(item, dict):
                            # Check if item has 'json' property (n8n standard format)
                            if 'json' in item:
                                json_data = item['json']
                                if isinstance(json_data, list):
                                    # If json contains a list, extend with all items
                                    all_records.extend(json_data)
                                elif isinstance(json_data, dict):
                                    # Check if it has 'sources' key
                                    if 'sources' in json_data:
                                        sources_data = json_data['sources']
                                        if isinstance(sources_data, list):
                                            all_records.extend(sources_data)
                                        elif isinstance(sources_data, dict):
                                            # Convert object with numeric keys to list
                                            sources_list = [sources_data[key] for key in sorted(sources_data.keys(), key=lambda x: int(x) if str(x).isdigit() else x)]
                                            all_records.extend(sources_list)
                                    else:
                                        # If json is a dict, it's a single record
                                        all_records.append(json_data)
                            else:
                                # No 'json' property, treat the item itself as a record
                                all_records.append(item)
                        elif isinstance(item, list):
                            # Item is a list, extend with all items
                            all_records.extend(item)
                    
                    if all_records:
                        summary_df = pd.DataFrame(all_records)
                        # Debug info
                        with st.expander("🔍 Debug: Parsing Info", expanded=False):
                            st.write(f"Total items in response: {len(result_data)}")
                            st.write(f"Total records extracted: {len(all_records)}")
                            st.write(f"Sources found: {[r.get('Source', 'N/A') for r in all_records[:10]]}")
                    else:
                        st.error("No records found in response")
                        st.json(result_data)
                        st.stop()
                elif isinstance(result_data, dict):
                    # Direct dict response
                    if 'sources' in result_data:
                        # Handle sources object (could be array or object with numeric keys)
                        sources_data = result_data['sources']
                        if isinstance(sources_data, list):
                            summary_df = pd.DataFrame(sources_data)
                        elif isinstance(sources_data, dict):
                            # Convert object with numeric keys to list
                            sources_list = [sources_data[key] for key in sorted(sources_data.keys(), key=lambda x: int(x) if str(x).isdigit() else x)]
                            summary_df = pd.DataFrame(sources_list)
                        else:
                            summary_df = pd.DataFrame([sources_data])
                    elif 'data' in result_data:
                        summary_df = pd.DataFrame(result_data['data'])
                    elif 'results' in result_data:
                        summary_df = pd.DataFrame(result_data['results'])
                    else:
                        # Try to create DataFrame from dict values
                        summary_df = pd.DataFrame([result_data])
                elif isinstance(result_data, list):
                    # Direct list response
                    summary_df = pd.DataFrame(result_data)
                else:
                    st.error(f"Unexpected response format: {type(result_data)}")
                    st.json(result_data)
                    st.stop()
                
            except ValueError as e:
                st.error(f"Failed to parse JSON response: {str(e)}")
                st.text(f"Response content: {response.text[:500]}")
                st.stop()
            except Exception as e:
                st.error(f"Error processing response: {str(e)}")
                st.exception(e)
                st.stop()
            
            # Display results as DataFrame
            st.markdown("### Sourcing Effectiveness Summary")
            
            # Check if we only got one source (likely n8n workflow issue)
            if len(summary_df) == 1:
                st.warning("⚠️ Only one source returned. Your n8n workflow should return ALL sources, not just one.")
                st.markdown("""
                **To fix in n8n:**
                - Make sure your Code node returns ALL sources in the `result` array
                - The code should loop through all sources and add each one to the result array
                - Check that `return result.map(row => ({json: row}));` includes all sources
                """)
            
            st.info(f"📊 Found {len(summary_df)} source(s) in the data")
            st.dataframe(summary_df, hide_index=True)
            st.success("✅ Data processed successfully!")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to n8n agent: {str(e)}")
            st.markdown("""
            **Troubleshooting steps:**
            1. **Check if n8n is running**: Open http://localhost:5678 in your browser
            2. **Verify webhook is active**: 
               - Go to your n8n workflow
               - Make sure the webhook node is **activated** (green toggle)
               - The workflow must be **active** (not just saved)
            3. **Check the webhook URL**: 
               - In n8n, click on the webhook node
               - Copy the exact webhook URL shown
               - Update it in the sidebar if different
            4. **Test the webhook**: Try accessing the webhook URL directly in your browser or with curl
            """)
            st.code(f"Current webhook URL: {n8n_webhook_url}", language="text")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
else:
    st.info("Please upload a CSV file to get started.")
