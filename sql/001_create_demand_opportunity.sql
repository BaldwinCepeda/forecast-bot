IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dc')
    EXEC('CREATE SCHEMA dc');
GO

CREATE TABLE dc.demand_opportunity (
    demand_opportunity_id        bigint         IDENTITY(1,1) NOT NULL PRIMARY KEY,
    canonical_demand_id          varchar(100)   NOT NULL,
    source_system                varchar(100)   NOT NULL,
    source_channel               varchar(30)    NOT NULL,
    source_record_id             varchar(100)   NULL,
    opportunity_reference        varchar(100)   NULL,
    record_type                  varchar(100)   NULL,
    client_name                  nvarchar(300)  NULL,
    client_name_key              nvarchar(300)  NULL,
    description                  nvarchar(2000) NULL,
    owner_name                   nvarchar(300)  NULL,
    owner_email                  varchar(320)   NULL,
    status_code                  varchar(30)    NULL,
    status_name                  nvarchar(200)  NULL,
    opportunity_stage            varchar(50)    NULL,
    source_forecast_window       nvarchar(100)  NULL,
    solution_due_at              datetime2(0)   NULL,
    estimated_close_at           datetime2(0)   NULL,
    created_at                   datetime2(0)   NULL,
    modified_at                  datetime2(0)   NULL,
    industry_group               varchar(100)   NULL,
    solution_area                nvarchar(300)  NULL,
    support_requested            nvarchar(300)  NULL,
    requested_by_email           varchar(320)   NULL,
    source_payload               nvarchar(max)  NULL,
    ingested_at_utc              datetime2(0)   NOT NULL
        CONSTRAINT DF_demand_opportunity_ingested_at DEFAULT SYSUTCDATETIME()
);
GO

CREATE INDEX IX_demand_opportunity_canonical_id
    ON dc.demand_opportunity (canonical_demand_id);

CREATE INDEX IX_demand_opportunity_channel
    ON dc.demand_opportunity (source_channel);

CREATE INDEX IX_demand_opportunity_reference
    ON dc.demand_opportunity (opportunity_reference);

CREATE INDEX IX_demand_opportunity_close_date
    ON dc.demand_opportunity (estimated_close_at);
GO
