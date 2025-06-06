#!/usr/bin/env python3
"""
Ekşi Sözlük Playwright Fetcher - OPTIMIZED VERSION
==================================================

Optimized for speed and performance with aggressive timeouts and concurrency.

Author: GitHub Copilot
Python: 3.8+
Libraries: playwright, pytz
"""

import asyncio
import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import pytz
from playwright.async_api import async_playwright, Page, Browser, Error as PlaywrightError

@dataclass
class CompanyInfo:
    """Company information container."""
    ticker: str
    official_name: str
    short_name: str
    common_names: List[str]
    eksi_search_terms: List[str]
    sector: str
    is_active: bool = True

# --- OPTIMIZED Configuration ---
BASE_URL = "https://eksisozluk.com"
OUTPUT_CSV_FILE = "eksi_latest_entries.csv"

# INCREASED TIMEOUTS FOR RELIABILITY (all in milliseconds)
REQUEST_TIMEOUT = 40000  # Increased to 20s for better reliability
PAGE_WAIT_TIMEOUT = 200  # Keep fast page waits
CONTENT_LOAD_TIMEOUT = 10000  # Increased to 10s
SELECTOR_WAIT_TIMEOUT = 8000  # Increased to 8s

# REDUCED RETRY CONFIGURATION
MAX_RETRIES = 2  # Reduced from 3 to 2
RETRY_INITIAL_BACKOFF_SEC = 0.5  # Reduced from 2.0s to 0.5s
RETRY_BACKOFF_FACTOR = 1.5  # Reduced from 2.0 to 1.5

# OPTIMIZED FOR ALL COMPANIES
MAX_CONCURRENT_WORKERS = 3  # Optimal performance with 3 workers

# REDUCED ENTRY LIMITS
ENTRIES_PER_COMPANY_LIMIT = 5  # Reduced from 10 per topic
TARGET_COMPANIES_FOR_DEBUG = 999999  # Process ALL companies

# --- Logging Setup ---
logging.basicConfig(level=logging.WARNING,  # Changed from INFO to WARNING for less output
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')  # Shorter time format
logger = logging.getLogger(__name__)

def load_companies_from_json(json_file_path: str) -> Dict[str, CompanyInfo]:
    """Load companies from JSON file - OPTIMIZED VERSION."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        companies = {}
        
        # Handle both old format {"companies": {...}} and new format [...]
        if isinstance(data, dict) and 'companies' in data:
            # Old format: {"companies": {...}}
            for ticker, company_data in data['companies'].items():
                companies[ticker] = CompanyInfo(
                    ticker=company_data['ticker'],
                    official_name=company_data['official_name'],
                    short_name=company_data['short_name'],
                    common_names=company_data['common_names'],
                    eksi_search_terms=company_data['eksi_search_terms'][:1],  # LIMIT TO 1 SEARCH TERM ONLY
                    sector=company_data['sector'],
                    is_active=company_data.get('is_active', True)
                )
        elif isinstance(data, list):
            # New format: [...]
            for company_data in data:
                ticker = company_data.get('ticker', '')
                companies[ticker] = CompanyInfo(
                    ticker=ticker,
                    official_name=company_data.get('official_name', ''),
                    short_name=company_data.get('short_name', ''),
                    common_names=company_data.get('common_names', []),
                    eksi_search_terms=company_data.get('eksi_search_terms', [])[:1],  # LIMIT TO 1 SEARCH TERM ONLY
                    sector=company_data.get('sector', 'unknown'),
                    is_active=company_data.get('is_active', True)
                )
        else:
            raise ValueError("Invalid JSON format")
        
        logger.warning(f"Loaded {len(companies)} companies (using only first search term per company)")
        return companies
    
    except Exception as e:
        logger.error(f"Error loading companies: {e}")
        raise

def parse_eksi_date_fast(date_str: str) -> Optional[datetime]:
    """Fast date parser - simplified version."""
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    now_istanbul = datetime.now(istanbul_tz)
    date_str = date_str.strip().lower()
    
    try:
        if "bugün" in date_str:
            time_part = date_str.replace("bugün", "").strip()
            dt_naive = datetime.strptime(time_part, "%H:%M").replace(
                year=now_istanbul.year, month=now_istanbul.month, day=now_istanbul.day
            )
        elif "dün" in date_str:
            yesterday = now_istanbul - timedelta(days=1)
            time_part = date_str.replace("dün", "").strip()
            dt_naive = datetime.strptime(time_part, "%H:%M").replace(
                year=yesterday.year, month=yesterday.month, day=yesterday.day
            )
        else:
            # Try standard formats quickly
            try:
                dt_naive = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
            except ValueError:
                try:
                    dt_naive = datetime.strptime(date_str, "%d.%m.%Y")
                except ValueError:
                    return None  # Skip complex parsing for speed
        
        if dt_naive:
            dt_istanbul = istanbul_tz.localize(dt_naive, is_dst=False)
            return dt_istanbul.astimezone(timezone.utc)
        
    except Exception:
        pass  # Silent fail for speed
    
    return None

async def get_topic_url_fast(page: Page, search_term: str) -> Optional[Tuple[str, int]]:
    """SIMPLE: Go to main page, get the real URL with topic ID, then go to last page"""
    # Simple URL construction
    url_term = search_term.lower()
    url_term = url_term.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
    url_term = url_term.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    url_term = url_term.replace(' ', '-').replace('.', '').replace(',', '')
    
    topic_url = f"{BASE_URL}/{url_term}"
    logger.warning(f"🔍 Going to main page: {topic_url}")
    
    try:
        # Go to main page
        await page.goto(topic_url, timeout=REQUEST_TIMEOUT, wait_until="domcontentloaded")
        
        # Check if entries exist
        try:
            await page.wait_for_selector("ul#entry-item-list > li", timeout=SELECTOR_WAIT_TIMEOUT)
        except:
            logger.warning(f"❌ No entries found")
            return None
        
        # Get the real URL (e.g., https://eksisozluk.com/agrot--7741030)
        real_url = page.url
        logger.warning(f"📍 Real URL: {real_url}")
        
        # Look for "son sayfa" link to get last page number
        try:
            await page.wait_for_selector("div.pager", timeout=3000)
            son_sayfa_link = await page.query_selector("div.pager a[title='son sayfa']")
            if son_sayfa_link:
                son_sayfa_href = await son_sayfa_link.get_attribute("href")
                # Extract page number (e.g., ?p=4 -> 4)
                if son_sayfa_href and '?p=' in son_sayfa_href:
                    last_page_num = int(son_sayfa_href.split('?p=')[1])
                    # Go to last page
                    last_page_url = f"{real_url}?p={last_page_num}"
                    logger.warning(f"🔚 Going to last page {last_page_num}: {last_page_url}")
                    await page.goto(last_page_url, timeout=REQUEST_TIMEOUT, wait_until="domcontentloaded")
                    await page.wait_for_selector("ul#entry-item-list > li", timeout=SELECTOR_WAIT_TIMEOUT)
                    return real_url, last_page_num
        except:
            pass
        
        # Single page topic
        logger.warning(f"📄 Single page topic")
        return real_url, 1
        
    except Exception as e:
        logger.warning(f"❌ Failed: {e}")
        return None

async def fetch_entries_fast(page: Page, topic_url: str, company: CompanyInfo, search_term: str, start_page_num: int = 1) -> List[Dict]:
    """FAST entry fetching - start from LAST PAGE (newest entries) and work BACKWARDS."""
    all_entries = []
    fetch_ts = datetime.now(timezone.utc)
    current_page = start_page_num
    
    try:
        # Start from LAST PAGE (newest entries) and go BACKWARDS
        while len(all_entries) < ENTRIES_PER_COMPANY_LIMIT and current_page >= 1:
            # Simple URL construction: base_url?p=X (or just base_url for page 1)
            if current_page == 1:
                target_url = topic_url
            else:
                target_url = f"{topic_url}?p={current_page}"
            
            logger.warning(f"📖 Page {current_page}: {target_url}")
            
            try:
                # Only navigate if we're not already there
                if page.url != target_url:
                    await page.goto(target_url, timeout=REQUEST_TIMEOUT, wait_until="domcontentloaded")
                
                await page.wait_for_selector("ul#entry-item-list > li", timeout=SELECTOR_WAIT_TIMEOUT)
                
                # Get entries from this page (REVERSE ORDER for newest first on each page)
                entry_elements = await page.query_selector_all("ul#entry-item-list > li")
                
                if not entry_elements:
                    logger.warning(f"📖 Page {current_page}: No entries found, stopping")
                    break
                
                # Process entries in REVERSE order within the page (newest first on each page)
                for entry_el in reversed(entry_elements):
                    if len(all_entries) >= ENTRIES_PER_COMPANY_LIMIT:
                        break
                        
                    try:
                        entry_id = await entry_el.get_attribute("data-id")
                        if not entry_id:
                            continue
                        
                        content_el = await entry_el.query_selector("div.content")
                        author_el = await entry_el.query_selector("footer div.info a.entry-author")
                        date_el = await entry_el.query_selector("footer div.info a.entry-date")
                        
                        if not all([content_el, author_el, date_el]):
                            continue
                        
                        content = (await content_el.inner_text()).strip() if content_el else ""
                        author = (await author_el.inner_text()).strip() if author_el else ""
                        date_str = (await date_el.inner_text()).strip() if date_el else ""
                        
                        entry_datetime = parse_eksi_date_fast(date_str)
                        
                        all_entries.append({
                            "company_ticker": company.ticker,
                            "company_official_name": company.official_name,
                            "search_term_used": search_term,
                            "topic_url": target_url,
                            "entry_id": entry_id,
                            "entry_content": content,
                            "entry_author": author,
                            "entry_date_str": date_str,
                            "entry_datetime_utc": entry_datetime.isoformat() if entry_datetime else None,
                            "fetch_timestamp_utc": fetch_ts.isoformat(),
                            "page_number": current_page,
                        })
                        
                    except Exception:
                        continue  # Skip failed entries
                
                logger.warning(f"📖 Page {current_page}: Got {len([e for e in all_entries if e['page_number'] == current_page])} entries")
                
            except Exception as e:
                logger.warning(f"❌ Failed to load page {current_page}: {e}")
                break  # Stop if page fails to load
            
            # Move to previous page (BACKWARDS)
            current_page -= 1
            
            # Small delay between pages
            await asyncio.sleep(0.5)
        
        logger.warning(f"📚 Total entries collected: {len(all_entries)} (from page {start_page_num} working BACKWARDS)")
        return all_entries
        
    except Exception as e:
        logger.warning(f"❌ Error in fetch_entries_fast: {e}")
        return all_entries

async def process_company_fast(browser: Browser, company: CompanyInfo, semaphore: asyncio.Semaphore) -> List[Dict]:
    """FAST company processing."""
    async with semaphore:
        context = None
        page = None
        try:
            # Lightweight browser context
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0"
            )
            page = await context.new_page()
            
            all_entries = []
            processed_urls = set()
            
            # Process only first search term for speed
            for term in company.eksi_search_terms[:1]:  # ONLY FIRST TERM
                topic_info = await get_topic_url_fast(page, term)
                if not topic_info:
                    continue
                
                topic_url, start_page_num = topic_info
                if topic_url in processed_urls:
                    continue
                processed_urls.add(topic_url)
                
                entries = await fetch_entries_fast(page, topic_url, company, term, start_page_num)
                all_entries.extend(entries)
                
                # Quick break if we have enough entries
                if len(all_entries) >= ENTRIES_PER_COMPANY_LIMIT:
                    break
            
            logger.warning(f"{company.ticker}: {len(all_entries)} entries")
            return all_entries
            
        except Exception as e:
            logger.error(f"Error processing {company.ticker}: {e}")
            return []
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass

def save_to_csv_fast(data: List[Dict], filename: str):
    """Fast CSV saving."""
    if not data:
        logger.warning("No data to save")
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        logger.warning(f"Saved {len(data)} entries to {filename}")
    except Exception as e:
        logger.error(f"Error saving CSV: {e}")

async def main():
    """OPTIMIZED main function."""
    start_time = datetime.now()
    logger.warning("Starting OPTIMIZED Ekşi Sözlük Fetcher...")
    
    # Load companies
    try:
        companies_dict = load_companies_from_json("companies.json")
        all_companies = list(companies_dict.values())
        
        # SKIP is_active filter - process all companies
        # active_companies = [c for c in all_companies if c.is_active]
        
        # DRASTICALLY REDUCE for speed testing
        companies_to_fetch = all_companies[:TARGET_COMPANIES_FOR_DEBUG]
        
        # Debug: Show what companies we're processing
        logger.warning("Companies to process:")
        for i, company in enumerate(companies_to_fetch):
            terms = ", ".join(company.eksi_search_terms[:1])  # Show only first term
            logger.warning(f"  {i+1}. {company.ticker} ({company.short_name}) - term: {terms}")
        
        logger.warning(f"Processing {len(companies_to_fetch)} companies with {MAX_CONCURRENT_WORKERS} workers")
    except Exception as e:
        logger.error(f"Failed to load companies: {e}")
        return
    
    all_entries = []
    
    async with async_playwright() as p:
        # Use Chromium for better performance
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']  # Performance args
        )
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKERS)
        
        try:
            logger.warning(f"Starting SEQUENTIAL processing of {len(companies_to_fetch)} companies...")
            
            # Sequential processing instead of parallel
            for i, company in enumerate(companies_to_fetch, 1):
                logger.warning(f"Processing {i}/{len(companies_to_fetch)}: {company.ticker}")
                
                try:
                    result = await process_company_fast(browser, company, semaphore)
                    if result:
                        all_entries.extend(result)
                        logger.warning(f"✅ {company.ticker}: Added {len(result)} entries (total: {len(all_entries)})")
                    else:
                        logger.warning(f"⚠️ {company.ticker}: No entries found")
                        
                    # Small delay between companies to be gentle on connection
                    if i < len(companies_to_fetch):  # Don't delay after last company
                        await asyncio.sleep(1)  # 1 second delay
                        
                except Exception as e:
                    logger.error(f"❌ {company.ticker}: Failed - {e}")
                    continue  # Continue with next company
                    
        finally:
            await browser.close()
    
    # Save results
    save_to_csv_fast(all_entries, OUTPUT_CSV_FILE)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.warning(f"COMPLETED: {len(all_entries)} entries in {duration:.1f}s ({len(all_entries)/duration:.1f} entries/sec)")

if __name__ == "__main__":
    print("🚀 Starting optimized Ekşi Sözlük fetcher...")
    import time
    start_time = time.time()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"⏱️  Total runtime: {time.time() - start_time:.1f}s")
