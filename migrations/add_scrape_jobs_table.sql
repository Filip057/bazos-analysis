-- Migration: Add scrape_jobs table for tracking web-triggered scraping jobs.
-- Each row represents one scraping session initiated from the admin UI.

CREATE TABLE IF NOT EXISTS scrape_jobs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    job_id      VARCHAR(50)  NOT NULL UNIQUE,
    status      VARCHAR(20)  NOT NULL DEFAULT 'queued',
    brands      TEXT         NULL,
    started_at  DATETIME     NULL,
    completed_at DATETIME    NULL,
    current_brand VARCHAR(50) NULL,
    brands_done TEXT         NULL,
    total_urls  INT          NOT NULL DEFAULT 0,
    processed_urls INT       NOT NULL DEFAULT 0,
    saved_count INT          NOT NULL DEFAULT 0,
    failed_count INT         NOT NULL DEFAULT 0,
    filtered_count INT       NOT NULL DEFAULT 0,
    error_message TEXT       NULL,
    worker_pid  INT          NULL,

    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
