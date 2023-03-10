import aiosqlite

class Database:
    def __init__(self, path):
        self.db_path = path

    async def _fetch(self, table: str, columns: list, condition: str, limit, values):

        if not columns:
            to_select = "*"
        else:
            to_select = ', '.join(columns)

        async with aiosqlite.connect(self.db_path) as db:
            c = await db.execute(
                f"""
                SELECT {to_select}
                  FROM {table}
                 {f'WHERE {condition}' if condition else ''}
                {f'LIMIT {limit}' if limit else ''}
                """, values
            )
            values = await c.fetchall()
            await c.close()

        return values

    async def fetchone(self, table: str, columns: list = None, condition: str = None, limit: int = None, **values):
        values = await self._fetch(table, columns, condition, limit, values)
        return values[0] if values else None

    async def fetchall(self, table: str, columns: list = None, condition: str = None, limit: int = None, **values):
        values = await self._fetch(table, columns, condition, limit, values)
        return values if values else None

    async def fetchval(self, table: str, column: str = None, condition: str = None, limit: int = None, **values):
        values = await self._fetch(table, [column], condition, limit, values)
        return values[0][0] if values else None

    async def update(self, table: str, columns: str, *condition, **values):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                UPDATE {table}
                    SET {columns}
                    {f'WHERE {condition}' if condition else ''}
                """, values
            )
            await db.commit()

    async def delete(self, table: str, condition: str = None, **values):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                DELETE FROM {table}
                   {f'WHERE {condition}' if condition else ''}
                """, values
            )
            await db.commit()

    async def insert(self, table: str, columns: list, **values):
        values_list = [v if v.startswith(":") else f':{v}' for v in columns]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                INSERT INTO {table} ({', '.join(columns)})
                     VALUES ({', '.join(values_list)})
                """, values
            )
            await db.commit()

