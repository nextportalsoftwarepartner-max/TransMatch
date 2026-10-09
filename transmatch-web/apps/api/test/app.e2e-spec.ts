import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import ExcelJS from 'exceljs';
import request from 'supertest';
import type TestAgent from 'supertest/lib/agent.js';
import { AppModule } from '../src/app.module.js';
import { setupApp } from '../src/app.setup.js';
import { Database } from '../src/database/database.js';
import { runMigrations } from '../src/database/migrator.js';
import { PgliteDatabase } from '../src/database/pglite-database.js';

// Runs the whole API against an in-memory PostgreSQL (PGlite) with the real migrations.
describe('TransMatch API (e2e)', () => {
  let app: INestApplication;
  let db: PgliteDatabase;
  let admin: TestAgent;

  beforeAll(async () => {
    process.env.NER_ML_ENABLED = 'false';
    db = new PgliteDatabase();
    await runMigrations(db);

    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(Database)
      .useValue(db)
      .compile();
    app = moduleRef.createNestApplication();
    setupApp(app);
    await app.init();

    admin = request.agent(app.getHttpServer());
    await admin.post('/api/auth/login').send({ loginId: 'superuser', password: '@@Adm123' }).expect(200);
  });

  afterAll(async () => {
    await app.close();
  });

  describe('schema', () => {
    it('generates combination keys as PP + YYMM + NNNNN and never repeats them', async () => {
      const [a] = await db.query<{ key: string }>(`SELECT tm.tm_generate_combination_key('ZZ') AS key`);
      const [b] = await db.query<{ key: string }>(`SELECT tm.tm_generate_combination_key('ZZ') AS key`);
      expect(a.key).toMatch(/^ZZ\d{4}00001$/);
      expect(b.key).toMatch(/^ZZ\d{4}00002$/);
    });

    it('restarts the sequence each month and rejects bad prefixes', async () => {
      const [row] = await db.query<{ key: string }>(
        `SELECT tm.tm_generate_combination_key('ZZ', TIMESTAMPTZ '2026-03-31 23:30+08') AS key`,
      );
      expect(row.key).toBe('ZZ260300001');
      await expect(db.query(`SELECT tm.tm_generate_combination_key('z1')`)).rejects.toThrow(/invalid entity prefix/);
    });

    it('stops at the monthly capacity instead of wrapping around', async () => {
      await db.query(
        `INSERT INTO tm.tm_mst_code_sequence (chr_entity_prefix, chr_period_yymm, num_last_sequence) VALUES ('ZY', '2501', 99999)`,
      );
      await expect(
        db.query(`SELECT tm.tm_generate_combination_key('ZY', TIMESTAMPTZ '2025-01-10 00:00+08')`),
      ).rejects.toThrow(/capacity/);
    });

    it('keeps creation fields immutable', async () => {
      await db.query(`UPDATE tm.tm_mst_user SET dtt_created_date = '2000-01-01', vch_user_name = vch_user_name`);
      const [row] = await db.query<{ year: number; modified: string | null }>(
        `SELECT extract(year FROM dtt_created_date)::int AS year, dtt_modified_date AS modified
         FROM tm.tm_mst_user WHERE vch_login_id = 'superuser'`,
      );
      expect(row.year).toBeGreaterThan(2000);
      expect(row.modified).not.toBeNull();
    });
  });

  describe('auth', () => {
    it('rejects requests without a session', async () => {
      await request(app.getHttpServer()).get('/api/groups').expect(401);
    });

    it('rejects a wrong password and records the attempt', async () => {
      await request(app.getHttpServer()).post('/api/auth/login').send({ loginId: 'superuser', password: 'nope' }).expect(401);
      const rows = await db.query<{ reason: string }>(
        `SELECT vch_failure_reason AS reason FROM tm.tm_his_login_log WHERE NOT bol_success_ind`,
      );
      expect(rows.map((r) => r.reason)).toContain('WRONG_PASSWORD');
    });

    it('returns the signed-in user', async () => {
      const res = await admin.get('/api/auth/me').expect(200);
      expect(res.body).toMatchObject({ loginId: 'superuser', isSuperUser: true });
      expect(res.body.userId).toMatch(/^US\d{9}$/);
    });
  });

  describe('administration', () => {
    let groupId: string;
    let roleId: string;

    it('creates a group and refuses a duplicate name', async () => {
      const res = await admin.post('/api/groups').send({ groupName: 'Kepong', groupDesc: 'Kepong area agency' }).expect(201);
      groupId = res.body.groupId;
      expect(groupId).toMatch(/^GP\d{9}$/);
      expect(res.body.createdBy).toBe('System Administrator');
      await admin.post('/api/groups').send({ groupName: 'KEPONG' }).expect(409);
      await admin.post('/api/groups').send({ groupName: '' }).expect(400);
    });

    it('protects the seeded super group', async () => {
      const groups = await admin.get('/api/groups?name=SUPER').expect(200);
      await admin.delete(`/api/groups/${groups.body[0].groupId}`).expect(403);
    });

    it('creates a role, grants it rights and enforces them', async () => {
      const role = await admin.post('/api/roles').send({ groupId, roleName: 'Data Entry', roleDesc: null }).expect(201);
      roleId = role.body.roleId;

      const permissions = await admin.get('/api/role-permissions/permissions').expect(200);
      expect(permissions.body).toHaveLength(17);
      const byCode = Object.fromEntries(permissions.body.map((p: { code: string; permissionId: string }) => [p.code, p.permissionId]));
      await admin
        .put(`/api/role-permissions/${roleId}`)
        .send({ items: [{ permissionId: byCode.ADM_BANK_PROFILE, rights: '10000000' }] })
        .expect(200);

      await admin
        .post('/api/users')
        .send({ roleId, loginId: 'agent1', userName: 'Agent One', password: 'Passw0rd!x' })
        .expect(201);

      const agent = request.agent(app.getHttpServer());
      const login = await agent.post('/api/auth/login').send({ loginId: 'agent1', password: 'Passw0rd!x' }).expect(200);
      expect(login.body.permissions).toEqual({ ADM_BANK_PROFILE: '10000000' });

      await agent.get('/api/banks').expect(200); // VIEW granted
      await agent.post('/api/banks').send({ bankName: 'Test Bank' }).expect(403); // CREATE not granted
      await agent.get('/api/groups').expect(403); // no permission at all

      // A group with roles cannot be deleted; deactivating it switches its users' rights off
      await admin.delete(`/api/groups/${groupId}`).expect(409);
      await admin.patch(`/api/groups/${groupId}/status`).send({ status: 'I' }).expect(200);
      await agent.get('/api/banks').expect(403);
      await admin.patch(`/api/groups/${groupId}/status`).send({ status: 'A' }).expect(200);
    });

    it('does not let a user delete their own account', async () => {
      const me = await admin.get('/api/auth/me');
      await admin.delete(`/api/users/${me.body.userId}`).expect(403);
    });

    it('imports names from Excel, skipping ones already listed', async () => {
      await admin.post('/api/blacklisted').send({ name: 'ACME TRADING' }).expect(204);

      const workbook = new ExcelJS.Workbook();
      const sheet = workbook.addWorksheet('Sheet1');
      sheet.addRows([['Blacklisted Name'], ['ACME TRADING'], ['SHADY ENTERPRISE'], [''], ['SHADY ENTERPRISE']]);
      const file = Buffer.from(await workbook.xlsx.writeBuffer());

      const res = await admin.post('/api/blacklisted/import').attach('file', file, 'names.xlsx').expect(201);
      expect(res.body).toEqual({ inserted: 1, skipped: 1 });

      const list = await admin.get('/api/blacklisted').expect(200);
      expect(list.body.map((r: { name: string }) => r.name).sort()).toEqual(['ACME TRADING', 'SHADY ENTERPRISE']);

      await admin.post('/api/suspicious').send({ name: 'acme trading' }).expect(204);
      const suspicious = await admin.get('/api/suspicious?existsInBlacklisted=Yes').expect(200);
      expect(suspicious.body).toHaveLength(1);
    });
  });

  describe('transactions and reports', () => {
    const batch = {
      source: 'MI',
      fileName: 'manual-oct',
      bank: { name: 'Public Bank', registrationNo: 'N/A', address: 'KL' },
      customer: { code: 'c001', name: 'ZANHERN BUILDER SDN. BHD.', address: 'PUCHONG' },
      accountNo: '0012345678',
      statementDate: '2026-10-31',
      transactions: [
        {
          transactionDate: '2026-10-02',
          description: 'TRANSFER FR A/C',
          descriptionOthers: 'ACME TRADING * rental',
          targetName: 'ACME TRADING',
          creditAmount: 0,
          debitAmount: 720,
          statementBalance: 11895.43,
        },
        {
          transactionDate: '2026-10-03',
          description: 'DUITNOW',
          descriptionOthers: 'TAN AH KOW',
          targetName: 'TAN AH KOW',
          creditAmount: 1500.5,
          debitAmount: 0,
          statementBalance: 13395.93,
        },
      ],
    };

    it('saves a manual batch, creating the bank and customer on the way', async () => {
      const res = await admin.post('/api/transactions/batches').send(batch).expect(201);
      expect(res.body.batchId).toMatch(/^IB\d{9}$/);
      expect(res.body.saved).toBe(2);

      const lookup = await admin.get('/api/transactions/lookups/customer-by-code?code=C001').expect(200);
      expect(lookup.body).toMatchObject({ found: true, customerName: 'ZANHERN BUILDER SDN. BHD.' });

      const rows = await db.query<{ account: string; agent: string }>(
        `SELECT t.vch_account_no AS account, u.vch_login_id AS agent
         FROM tm.tm_trn_transaction t JOIN tm.tm_mst_user u ON u.vch_user_id = t.vch_created_by`,
      );
      expect(rows).toHaveLength(2);
      expect(rows[0]).toEqual({ account: '0012345678', agent: 'superuser' });
    });

    it('refuses a customer code that belongs to another customer, saving nothing', async () => {
      await admin
        .post('/api/transactions/batches')
        .send({ ...batch, customer: { ...batch.customer, name: 'SOMEONE ELSE' } })
        .expect(409);
      const [count] = await db.query<{ n: number }>('SELECT count(*) AS n FROM tm.tm_trn_transaction');
      expect(count.n).toBe(2);
    });

    it('searches and edits a transaction (data enrichment)', async () => {
      const list = await admin.get('/api/transactions?customerCode=C001&dateFrom=2026-10-01&dateTo=2026-10-02').expect(200);
      expect(list.body).toHaveLength(1);
      expect(list.body[0]).toMatchObject({ description: 'TRANSFER FR A/C ACME TRADING * rental', transactionDate: '2026-10-02' });

      const id = list.body[0].transactionId;
      const detail = await admin.get(`/api/transactions/${id}`).expect(200);
      expect(detail.body).toMatchObject({ debitAmount: 720, statementBalance: 11895.43, printed: false });

      const updated = await admin
        .put(`/api/transactions/${id}`)
        .send({ ...detail.body, targetName: 'ACME TRADING SDN BHD', printed: true })
        .expect(200);
      expect(updated.body).toMatchObject({ targetName: 'ACME TRADING SDN BHD', printed: true });
    });

    it('flags blacklisted transactions on enquiry and filters by condition', async () => {
      const all = await admin.get('/api/reports/enquiry').expect(200);
      expect(all.body.rows).toHaveLength(2);
      const statuses = Object.fromEntries(
        all.body.rows.map((r: { transactionDate: string; watchStatus: string }) => [r.transactionDate, r.watchStatus]),
      );
      expect(statuses).toEqual({ '2026-10-02': 'BLACKLISTED', '2026-10-03': 'NONE' });

      const blacklisted = await admin.get('/api/reports/enquiry?condition=Blacklisted').expect(200);
      expect(blacklisted.body.rows).toHaveLength(1);
      const printed = await admin.get('/api/reports/enquiry?printed=Yes').expect(200);
      expect(printed.body.rows).toHaveLength(1);
    });

    it('exports the selected transactions as text and Excel', async () => {
      const all = await admin.get('/api/reports/enquiry').expect(200);
      const transactionIds = all.body.rows.map((r: { transactionId: string }) => r.transactionId);

      const text = await admin.post('/api/reports/enquiry/export/text').send({ transactionIds }).expect(200);
      expect(text.body.text).toContain('Customer ID: C001');
      expect(text.body.text).toContain('BLACKLISTED\n===================================\nACME TRADING');
      expect(text.body.text).toContain('02-Oct-26 | RM -720.00');
      expect(text.body.text).toContain('TAN AH KOW\n- - - - - - - - - - - - - - - -\n03-Oct-26 | RM +1,500.50');
      expect(text.body.text).toContain('Agent Name: System Administrator');

      const excel = await admin
        .post('/api/reports/enquiry/export/excel')
        .send({ transactionIds })
        .buffer(true)
        .parse((res, done) => {
          const chunks: Buffer[] = [];
          res.on('data', (c: Buffer) => chunks.push(c));
          res.on('end', () => done(null, Buffer.concat(chunks)));
        })
        .expect(200);
      const workbook = new ExcelJS.Workbook();
      await workbook.xlsx.load(excel.body);
      const sheet = workbook.worksheets[0];
      expect(sheet.getCell('A1').text).toBe('Customer ID: C001');
      // Rows 1-4 are the customer heading; data rows follow, newest transaction first
      expect(sheet.getRow(5).getCell(2).text).toBe('Others');
      expect(sheet.getRow(6).getCell(2).text).toBe('Blacklisted');
    });
  });
});
