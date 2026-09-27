BEGIN;
DO $$
DECLARE
  item record;
  doc json;
  version_id text;
  was_active boolean;
BEGIN
  FOR item IN
    SELECT * FROM (VALUES
      ('/tmp/runtime-01.json', 'CSWF000000000001'),
      ('/tmp/runtime-03.json', 'CSWF000000000003'),
      ('/tmp/runtime-04B.json', 'CSWF000000000005'),
      ('/tmp/runtime-05.json', 'CSWF000000000007')
    ) AS f(path, workflow_id)
  LOOP
    doc := pg_read_file(item.path)::json;
    IF doc->>'id' <> item.workflow_id THEN
      RAISE EXCEPTION 'Workflow ID mismatch in %', item.path;
    END IF;
    SELECT active INTO was_active FROM workflow_entity WHERE id=item.workflow_id FOR UPDATE;
    IF was_active IS DISTINCT FROM true THEN
      RAISE EXCEPTION 'Refusing to update inactive workflow %', item.workflow_id;
    END IF;
    version_id := doc->>'versionId';
    INSERT INTO workflow_history("versionId", "workflowId", authors, nodes, connections, name, description)
    VALUES(version_id, item.workflow_id, 'runtime forensic recovery', doc->'nodes', doc->'connections', doc->>'name', doc->>'description')
    ON CONFLICT ("versionId") DO NOTHING;
    UPDATE workflow_entity
       SET nodes=doc->'nodes', connections=doc->'connections', settings=doc->'settings',
           "staticData"=doc->'staticData', "pinData"=doc->'pinData',
           "versionId"=version_id, "activeVersionId"=version_id,
           "versionCounter"="versionCounter"+1, "updatedAt"=now()
     WHERE id=item.workflow_id;
  END LOOP;
END $$;
COMMIT;


