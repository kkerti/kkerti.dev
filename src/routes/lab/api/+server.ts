import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, platform }) => {
    try {
        const body = await request.json();
        
        // Validate that temperature field exists
        if (!body.hasOwnProperty('temperature')) {
            return json({ 
                error: 'temperature field is required',
                ok: false 
            }, { status: 400 });
        }

        // Validate temperature is a number and within reasonable range
        const temperature = parseFloat(body.temperature);
        if (isNaN(temperature) || temperature < -50 || temperature > 100) {
            return json({ 
                error: 'temperature must be a number between -50 and 100',
                ok: false 
            }, { status: 400 });
        }

        // Get database from platform
        const db = platform?.env?.DB;
        if (!db) {
            return json({ 
                error: 'Database not available',
                ok: false 
            }, { status: 500 });
        }

        // Insert temperature reading into database
        const result = await db.prepare(
            'INSERT INTO temperature_readings (temperature, device_id, timestamp, metadata) VALUES (?, ?, ?, ?)'
        ).bind(
            temperature,
            body.device_id,
            body.timestamp,
            body.metadata ? JSON.stringify(body.metadata) : null
        ).run();

        return json({
            ok: true,
            id: result.meta.last_row_id,
            message: 'Temperature reading saved successfully'
        });

    } catch (error) {
        console.error('Error saving temperature:', error);
        return json({ 
            error: 'Failed to save temperature reading',
            ok: false 
        }, { status: 500 });
    }
};

export const GET: RequestHandler = async ({ url, platform }) => {
    try {
        // Get database from platform
        const db = platform?.env?.DB;
        if (!db) {
            return json({ 
                error: 'Database not available',
                ok: false 
            }, { status: 500 });
        }

        // Get query parameters
        const limit = Math.min(parseInt(url.searchParams.get('limit') || '100'), 1000);
        const offset = parseInt(url.searchParams.get('offset') || '0');
        const location = url.searchParams.get('location');

        // Build query
        let query = 'SELECT * FROM temperature_readings';
        const params = [];

        if (location) {
            query += ' WHERE location = ?';
            params.push(location);
        }

        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?';
        params.push(limit, offset);

        // Execute query
        const { results } = await db.prepare(query).bind(...params).all();

        // Also get total count
        let countQuery = 'SELECT COUNT(*) as total FROM temperature_readings';
        const countParams = [];
        
        if (location) {
            countQuery += ' WHERE location = ?';
            countParams.push(location);
        }

        const { results: countResults } = await db.prepare(countQuery).bind(...countParams).all();
        const total = countResults[0]?.total || 0;

        console.log(results)

        return json({
            ok: true,
            data: results,
            meta: {
                total,
                limit,
                offset,
                hasMore: offset + limit < total
            }
        });

    } catch (error) {
        console.error('Error fetching temperature data:', error);
        return json({ 
            error: 'Failed to fetch temperature readings',
            ok: false 
        }, { status: 500 });
    }
};