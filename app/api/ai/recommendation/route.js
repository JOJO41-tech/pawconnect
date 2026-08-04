import { NextResponse } from "next/server";
import db from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request) {
  try {
    const body = await request.json();
    const text = body?.text?.trim();

    if (!text) {
      return NextResponse.json(
        {
          error: "Please describe your lifestyle and pet preferences.",
        },
        { status: 400 }
      );
    }

    const aiApiUrl = process.env.AI_API_URL?.trim();

    if (!aiApiUrl) {
      console.error("AI_API_URL is missing.");

      return NextResponse.json(
        {
          error: "The AI service is not configured.",
        },
        { status: 500 }
      );
    }

    // Retrieve available pets from TiDB/MySQL.
    const [animals] = await db.query(`
      SELECT
        id,
        shelter_id,
        name,
        type,
        breed,
        size,
        age,
        gender,
        temperament,
        location,
        health_status,
        vaccination_status,
        sterilization_status,
        description,
        image_url,
        adoption_status,
        energy_level,
        apartment_friendly,
        child_friendly,
        pet_friendly,
        experience_required,
        daily_attention_hours
      FROM animals
      WHERE LOWER(adoption_status) = 'available'
      ORDER BY id DESC
      LIMIT 100
    `);

    if (!Array.isArray(animals) || animals.length === 0) {
      return NextResponse.json(
        {
          error: "No available animals were found.",
        },
        { status: 404 }
      );
    }

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 60000);

    let aiResponse;

    try {
      const normalizedAiUrl = aiApiUrl.replace(/\/+$/, "");

      aiResponse = await fetch(`${normalizedAiUrl}/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          animals,
        }),
        cache: "no-store",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    const responseText = await aiResponse.text();

    let result;

    try {
      result = responseText ? JSON.parse(responseText) : {};
    } catch {
      result = {
        error: "The AI service returned an invalid response.",
        details: responseText.slice(0, 500),
      };
    }

    if (!aiResponse.ok) {
      console.error("AI service error:", {
        status: aiResponse.status,
        result,
      });

      return NextResponse.json(
        {
          error:
            result?.error ||
            result?.detail ||
            "The AI recommendation service failed.",
          details: result?.details || null,
        },
        { status: aiResponse.status }
      );
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error("AI recommendation route error:", error);

    if (error?.name === "AbortError") {
      return NextResponse.json(
        {
          error: "The AI service took too long to respond.",
        },
        { status: 504 }
      );
    }

    return NextResponse.json(
      {
        error:
          process.env.NODE_ENV === "development"
            ? error?.message || "Failed to generate recommendations."
            : "Failed to generate recommendations.",
      },
      { status: 500 }
    );
  }
}