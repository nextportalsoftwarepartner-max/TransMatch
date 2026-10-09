import { Module } from '@nestjs/common';
import { GroupsController, RolePermissionsController, RolesController, UsersController } from './access.controller.js';
import { BanksService } from './banks.service.js';
import { CustomersService } from './customers.service.js';
import { GroupsService } from './groups.service.js';
import { BanksController, BlacklistedController, CustomersController, SuspiciousController } from './masters.controller.js';
import { RolesService } from './roles.service.js';
import { UsersService } from './users.service.js';
import { WatchlistService } from './watchlist.service.js';

@Module({
  controllers: [
    GroupsController,
    RolesController,
    RolePermissionsController,
    UsersController,
    CustomersController,
    BanksController,
    BlacklistedController,
    SuspiciousController,
  ],
  providers: [GroupsService, RolesService, UsersService, CustomersService, BanksService, WatchlistService],
  exports: [CustomersService, BanksService, UsersService, WatchlistService],
})
export class AdminModule {}
