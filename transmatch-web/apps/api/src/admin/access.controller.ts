import { Body, Controller, Delete, Get, HttpCode, Param, Patch, Post, Put, Query } from '@nestjs/common';
import {
  createUserSchema,
  groupSchema,
  PERMISSIONS,
  resetPasswordSchema,
  rolePermissionsSchema,
  roleSchema,
  statusSchema,
  updateUserSchema,
  type RolePermissionsInput,
  type SessionUser,
} from '@transmatch/shared';
import type { z } from 'zod';
import { CurrentUser, RequirePermission } from '../auth/auth.decorators.js';
import { ZodPipe } from '../common/zod.pipe.js';
import { GroupsService } from './groups.service.js';
import { RolesService } from './roles.service.js';
import { UsersService } from './users.service.js';

type StatusBody = z.infer<typeof statusSchema>;

@Controller('groups')
@RequirePermission(PERMISSIONS.ADM_USER_GROUP)
export class GroupsController {
  constructor(private readonly groups: GroupsService) {}

  @Get()
  list(@Query('name') name?: string) {
    return this.groups.list(name?.trim() || undefined);
  }

  @Post()
  @RequirePermission(PERMISSIONS.ADM_USER_GROUP, 'CREATE')
  create(@Body(new ZodPipe(groupSchema)) body: z.infer<typeof groupSchema>, @CurrentUser() user: SessionUser) {
    return this.groups.create(body, user.userId);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.ADM_USER_GROUP, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(groupSchema)) body: z.infer<typeof groupSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.groups.update(id, body, user.userId);
  }

  @Patch(':id/status')
  @RequirePermission(PERMISSIONS.ADM_USER_GROUP, 'UPDATE')
  setStatus(@Param('id') id: string, @Body(new ZodPipe(statusSchema)) body: StatusBody, @CurrentUser() user: SessionUser) {
    return this.groups.setStatus(id, body.status, user.userId);
  }

  @Delete(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_USER_GROUP, 'DELETE')
  remove(@Param('id') id: string, @CurrentUser() user: SessionUser) {
    return this.groups.remove(id, user.userId);
  }
}

@Controller('roles')
@RequirePermission(PERMISSIONS.ADM_USER_ROLE)
export class RolesController {
  constructor(
    private readonly roles: RolesService,
    private readonly groups: GroupsService,
  ) {}

  @Get()
  list(@Query('name') name?: string, @Query('groupId') groupId?: string) {
    return this.roles.list({ name: name?.trim() || undefined, groupId: groupId || undefined });
  }

  /** Active groups for the group picker on the role screen. */
  @Get('group-options')
  async groupOptions() {
    return (await this.groups.list()).filter((g) => g.status === 'A');
  }

  @Post()
  @RequirePermission(PERMISSIONS.ADM_USER_ROLE, 'CREATE')
  create(@Body(new ZodPipe(roleSchema)) body: z.infer<typeof roleSchema>, @CurrentUser() user: SessionUser) {
    return this.roles.create(body, user.userId);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.ADM_USER_ROLE, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(roleSchema)) body: z.infer<typeof roleSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.roles.update(id, body, user.userId);
  }

  @Patch(':id/status')
  @RequirePermission(PERMISSIONS.ADM_USER_ROLE, 'UPDATE')
  setStatus(@Param('id') id: string, @Body(new ZodPipe(statusSchema)) body: StatusBody, @CurrentUser() user: SessionUser) {
    return this.roles.setStatus(id, body.status, user.userId);
  }

  @Delete(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_USER_ROLE, 'DELETE')
  remove(@Param('id') id: string, @CurrentUser() user: SessionUser) {
    return this.roles.remove(id, user.userId);
  }
}

/** "User Rights": which screens a role may use, and what it may do on them. */
@Controller('role-permissions')
@RequirePermission(PERMISSIONS.ADM_USER_RIGHTS)
export class RolePermissionsController {
  constructor(private readonly roles: RolesService) {}

  @Get('permissions')
  permissions() {
    return this.roles.listPermissions();
  }

  @Get('roles')
  roleOptions() {
    return this.roles.list({});
  }

  @Get(':roleId')
  get(@Param('roleId') roleId: string) {
    return this.roles.getRolePermissions(roleId);
  }

  @Put(':roleId')
  @RequirePermission(PERMISSIONS.ADM_USER_RIGHTS, 'UPDATE')
  set(
    @Param('roleId') roleId: string,
    @Body(new ZodPipe(rolePermissionsSchema)) body: RolePermissionsInput,
    @CurrentUser() user: SessionUser,
  ) {
    return this.roles.setRolePermissions(roleId, body, user.userId);
  }
}

@Controller('users')
@RequirePermission(PERMISSIONS.ADM_USER_PROFILE)
export class UsersController {
  constructor(
    private readonly users: UsersService,
    private readonly groups: GroupsService,
    private readonly roles: RolesService,
  ) {}

  @Get()
  list(@Query('groupId') groupId?: string, @Query('roleId') roleId?: string, @Query('name') name?: string) {
    return this.users.list({ groupId: groupId || undefined, roleId: roleId || undefined, name: name?.trim() || undefined });
  }

  /** Groups and roles for the pickers on the user profile screen. */
  @Get('form-options')
  async formOptions() {
    const [groups, roles, users] = await Promise.all([this.groups.list(), this.roles.list({}), this.users.options()]);
    return {
      groups: groups.filter((g) => g.status === 'A'),
      roles: roles.filter((r) => r.status === 'A'),
      supervisors: users,
    };
  }

  @Post()
  @RequirePermission(PERMISSIONS.ADM_USER_PROFILE, 'CREATE')
  create(@Body(new ZodPipe(createUserSchema)) body: z.infer<typeof createUserSchema>, @CurrentUser() user: SessionUser) {
    return this.users.create(body, user.userId);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.ADM_USER_PROFILE, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(updateUserSchema)) body: z.infer<typeof updateUserSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.users.update(id, body, user.userId);
  }

  @Post(':id/reset-password')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_USER_PROFILE, 'UPDATE')
  resetPassword(
    @Param('id') id: string,
    @Body(new ZodPipe(resetPasswordSchema)) body: z.infer<typeof resetPasswordSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.users.resetPassword(id, body.newPassword, user.userId);
  }

  @Delete(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_USER_PROFILE, 'DELETE')
  remove(@Param('id') id: string, @CurrentUser() user: SessionUser) {
    return this.users.remove(id, user.userId);
  }
}
