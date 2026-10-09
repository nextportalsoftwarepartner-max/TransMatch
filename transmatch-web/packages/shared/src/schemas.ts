import { z } from 'zod';

// ---- Building blocks ----

const text = (max: number) => z.string().trim().max(max);
const requiredText = (max: number, label: string) => text(max).min(1, `${label} is required.`);
const optionalText = (max: number) =>
  text(max)
    .nullish()
    .transform((v) => v || null);
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Expected a date in YYYY-MM-DD format.');
const optionalIsoDate = isoDate.nullish().transform((v) => v || null);
const amount = z.coerce.number().finite().min(0).max(9_999_999_999_999.99);
const signedAmount = z.coerce.number().finite().min(-9_999_999_999_999.99).max(9_999_999_999_999.99);
const id = z.string().trim().min(1).max(15);
const status = z.enum(['A', 'I']);
const matchType = z.enum(['Equal', 'Contain']).default('Equal');
const queryText = z
  .string()
  .trim()
  .optional()
  .transform((v) => v || undefined);

// ---- Auth ----

export const loginSchema = z.object({
  loginId: requiredText(100, 'Username'),
  password: z.string().min(1, 'Password is required.').max(200),
});
export type LoginInput = z.infer<typeof loginSchema>;

const newPassword = z.string().min(8, 'Password must be at least 8 characters.').max(200);

export const changePasswordSchema = z.object({
  currentPassword: z.string().min(1).max(200),
  newPassword,
});
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;

// ---- User group / role / rights ----

export const groupSchema = z.object({
  groupName: requiredText(50, 'Group Name'),
  groupDesc: optionalText(100),
});
export type GroupInput = z.input<typeof groupSchema>;

export const roleSchema = z.object({
  groupId: id,
  roleName: requiredText(50, 'Role Name'),
  roleDesc: optionalText(255),
});
export type RoleInput = z.input<typeof roleSchema>;

export const statusSchema = z.object({ status });

export const rolePermissionsSchema = z.object({
  items: z
    .array(
      z.object({
        permissionId: id,
        rights: z.string().regex(/^[01]{8}$/),
      }),
    )
    .max(200),
});
export type RolePermissionsInput = z.infer<typeof rolePermissionsSchema>;

// ---- User profile ----

const userFields = {
  roleId: id,
  loginId: requiredText(100, 'Login ID'),
  userName: requiredText(100, 'Staff Name'),
  supervisorUserId: id.nullish().transform((v) => v || null),
  email: optionalText(100),
  contactNo: optionalText(20),
  address1: optionalText(255),
  address2: optionalText(255),
  address3: optionalText(255),
  address4: optionalText(255),
};
export const createUserSchema = z.object({ ...userFields, password: newPassword });
export const updateUserSchema = z.object(userFields);
export const resetPasswordSchema = z.object({ newPassword });
export type CreateUserInput = z.input<typeof createUserSchema>;
export type UpdateUserInput = z.input<typeof updateUserSchema>;

// ---- Customer / bank ----

export const customerSchema = z.object({
  customerCode: requiredText(30, 'Customer Code').transform((v) => v.toUpperCase()),
  customerName: requiredText(100, 'Customer Name').transform((v) => v.toUpperCase()),
  email: optionalText(100),
  contactNo: optionalText(20),
  address: optionalText(255),
});
export type CustomerInput = z.input<typeof customerSchema>;

export const customerRemarkSchema = z.object({ remark: optionalText(4000) });

export const bankSchema = z.object({
  bankName: requiredText(100, 'Bank Name'),
  bankDisplayName: optionalText(50),
  bankRegNo: optionalText(255),
  bankAddress: optionalText(255),
});
export type BankInput = z.input<typeof bankSchema>;

// ---- Blacklisted / suspicious names ----

export const watchNameSchema = z.object({ name: requiredText(100, 'Name') });
export const deleteManySchema = z.object({ ids: z.array(id).min(1).max(1000) });

// ---- Transactions ----

export const transactionRowSchema = z
  .object({
    transactionDate: isoDate,
    description: text(1000).default(''),
    descriptionOthers: text(4000).default(''),
    targetName: text(255).default(''),
    creditAmount: signedAmount.default(0),
    debitAmount: signedAmount.default(0),
    statementBalance: signedAmount.default(0),
  })
  .strict();
export type TransactionRowInput = z.input<typeof transactionRowSchema>;

export const saveBatchSchema = z.object({
  /** PU = PDF upload, MI = manual input */
  source: z.enum(['PU', 'MI']),
  fileName: optionalText(255),
  bank: z.object({
    name: requiredText(100, 'Bank Name'),
    registrationNo: optionalText(255),
    address: optionalText(255),
  }),
  customer: z.object({
    code: requiredText(30, 'Customer Code').transform((v) => v.toUpperCase()),
    name: requiredText(100, 'Customer Name'),
    address: optionalText(255),
  }),
  accountNo: optionalText(30),
  statementDate: isoDate,
  transactions: z.array(transactionRowSchema).min(1, 'No transaction records found.').max(20000),
});
export type SaveBatchInput = z.input<typeof saveBatchSchema>;

export const updateTransactionSchema = z.object({
  fileName: optionalText(255),
  bankId: id,
  customerId: id,
  agentUserId: id,
  accountNo: optionalText(30),
  statementDate: optionalIsoDate,
  transactionDate: isoDate,
  description: text(1000).default(''),
  descriptionOthers: text(4000).default(''),
  targetName: text(255).default(''),
  creditAmount: amount.default(0),
  debitAmount: amount.default(0),
  statementBalance: signedAmount.default(0),
  printed: z.boolean(),
});
export type UpdateTransactionInput = z.input<typeof updateTransactionSchema>;

// ---- Search filters (query strings) ----

const dateFilter = {
  dateType: z.enum(['transaction', 'entry']).default('transaction'),
  dateFrom: isoDate.optional(),
  dateTo: isoDate.optional(),
};

export const enrichmentSearchSchema = z.object({
  customerCode: queryText,
  customerName: queryText,
  customerNameMatch: matchType,
  accountNo: queryText,
  targetName: queryText,
  fileName: queryText,
  description: queryText,
  descriptionMatch: matchType,
  ...dateFilter,
});
export type EnrichmentSearch = z.input<typeof enrichmentSearchSchema>;

export const ENQUIRY_CONDITIONS = ['All', 'Blacklisted', 'Blacklisted-PartialMatch', 'Suspicious', 'Whitelist'] as const;

export const enquirySearchSchema = z.object({
  customerCode: queryText,
  customerName: queryText,
  customerNameMatch: matchType,
  description: queryText,
  descriptionMatch: matchType,
  bankName: queryText,
  fileName: queryText,
  condition: z.enum(ENQUIRY_CONDITIONS).default('All'),
  printed: z.enum(['All', 'Yes', 'No']).default('All'),
  agentUserId: queryText,
  ...dateFilter,
});
export type EnquirySearch = z.input<typeof enquirySearchSchema>;

export const exportSchema = z.object({ transactionIds: z.array(id).min(1).max(50000) });
