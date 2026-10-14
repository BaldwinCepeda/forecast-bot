-- Companion Azure SQL objects for dc.demand_opportunity.
-- Run 001_create_demand_opportunity.sql before this script.
IF COL_LENGTH('dc.demand_opportunity', 'source_forecast_window') IS NULL
    ALTER TABLE dc.demand_opportunity ADD source_forecast_window nvarchar(100) NULL;
GO
IF COL_LENGTH('dc.demand_opportunity', 'source_payload') IS NULL
    ALTER TABLE dc.demand_opportunity ADD source_payload nvarchar(max) NULL;
GO
IF COL_LENGTH('dc.demand_opportunity', 'demand_opportunity_id') IS NULL
BEGIN
    ALTER TABLE dc.demand_opportunity ADD demand_opportunity_id bigint IDENTITY(1,1) NOT NULL;
    DECLARE @demand_pk sysname;
    SELECT @demand_pk = kc.name
    FROM sys.key_constraints kc
    JOIN sys.index_columns ic ON ic.object_id = kc.parent_object_id AND ic.index_id = kc.unique_index_id
    JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
    WHERE kc.parent_object_id = OBJECT_ID('dc.demand_opportunity')
      AND kc.type = 'PK'
      AND c.name = 'canonical_demand_id';
    IF @demand_pk IS NOT NULL
        EXEC('ALTER TABLE dc.demand_opportunity DROP CONSTRAINT ' + QUOTENAME(@demand_pk));
    ALTER TABLE dc.demand_opportunity ADD CONSTRAINT PK_demand_opportunity_row
        PRIMARY KEY (demand_opportunity_id);
    CREATE INDEX IX_demand_opportunity_canonical_id
        ON dc.demand_opportunity(canonical_demand_id);
END;
GO
ALTER TABLE dc.demand_opportunity ALTER COLUMN source_record_id varchar(100) NULL;
GO

IF OBJECT_ID('dc.role_estimate', 'U') IS NULL
BEGIN
    CREATE TABLE dc.role_estimate (
        role_estimate_id       varchar(100)   NOT NULL PRIMARY KEY,
        canonical_demand_id    varchar(100)   NOT NULL,
        role_title             nvarchar(300)  NULL,
        primary_skill          nvarchar(200)  NULL,
        career_level           nvarchar(100)  NULL,
        quantity               decimal(12, 2) NULL,
        expected_start_date    date           NULL,
        confidence_override    decimal(5, 4)  NULL,
        geography              nvarchar(200)  NULL,
        notes                  nvarchar(max)  NULL,
        created_at             datetime2(0)   NULL,
        updated_at             datetime2(0)   NULL
        -- No FK: malformed or duplicate source IDs are retained and flagged by the pipeline.
    );
    CREATE INDEX IX_role_estimate_demand ON dc.role_estimate(canonical_demand_id);
END;
GO

IF OBJECT_ID('dc.data_quality_issue', 'U') IS NULL
BEGIN
    CREATE TABLE dc.data_quality_issue (
        data_quality_issue_id  bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        canonical_demand_id    varchar(100)   NULL,
        source_channel         nvarchar(100)  NULL,
        issue_code             varchar(100)   NOT NULL,
        issue_description      nvarchar(max)  NOT NULL,
        severity               varchar(30)    NOT NULL,
        detected_at_utc        datetime2(0)   NOT NULL
    );
END;
GO